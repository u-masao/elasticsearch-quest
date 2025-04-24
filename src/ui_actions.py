import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import gradio as gr
from elasticsearch.helpers import bulk

from src.bootstrap import AppContainer
from src.config import load_config
from src.exceptions import QuestCliError
from src.services.agent_service import AgentService
from src.services.core_logic import execute_query as core_logic_execute_query
from src.services.quest_service import QuestService
from src.ui_asset import JSON_CHECK_NG, JSON_CHECK_OK, SUBMIT_BUTTON_TEXT

# リファクタリングで分割・作成したモジュールをインポート
from src.utils.query_loader import load_query_from_source
from src.view import EndOfMessage, QuestView


class QueuedQuestView(QuestView):
    """非同期メッセージキューを持つQuestViewの拡張クラス"""

    def __init__(self):
        super().__init__()
        self.message_queue = asyncio.Queue()  # 非同期メッセージキューを追加
        self.custom_echo = self.send_message

    async def send_message(self, message: str | EndOfMessage, **kwargs: Dict[str, Any]):
        """非同期にメッセージをキューに送信する"""
        await self.message_queue.put(message)

    async def receive_messages(self):
        """キューからメッセージを取り出して処理する非同期メソッド"""
        while True:
            message = await self.message_queue.get()
            self.message_queue.task_done()
            if isinstance(message, EndOfMessage):
                break
            elif isinstance(message, str):
                yield message
            else:
                raise ValueError(
                    f"receive_messages で予期しない型を受け取りました: {type(message)}"
                )


async def handle_exception(view: QuestView, e: Exception):
    """集約的な例外ハンドリング"""
    if isinstance(e, (QuestCliError, FileNotFoundError)):
        msg = (
            str(e)
            if isinstance(e, QuestCliError)
            else f"必要なファイルが見つかりません: {e}"
        )
        await view.display_error(msg)
    else:
        await view.display_error(
            f"予期せぬエラーが発生しました: {type(e).__name__}: {e}"
        )


async def get_services(
    view: QueuedQuestView | None = None,
    db_path_override: Path | None = None,
    index_name_override: str | None = None,
    book_path_override: Path | None = None,
) -> Tuple[Any, Any, Any, QuestService, AgentService]:
    """
    サービス初期化を行い、関連インスタンスを返すヘルパー関数。
    """
    if view is None:
        view = QueuedQuestView()
    config = load_config(
        db_path_override=db_path_override,
        index_name_override=index_name_override,
        book_path_override=book_path_override,
    )
    container = AppContainer(config, view)
    quest_repo = await container.quest_repository
    es_client = await container.es_client
    quest_service = QuestService(quest_repo, es_client, config.index_name)
    agent_service = AgentService(config, view)
    return config, quest_repo, es_client, quest_service, agent_service


async def cli(
    quest_id: int,
    view: QueuedQuestView | None = None,
    query: str | None = None,
    query_file: Path | None = None,
    db_path: Path | None = None,
    index_name: str | None = None,
    skip_agent: bool = False,
):
    try:
        (
            config,
            quest_repo,
            es_client,
            quest_service,
            agent_service,
        ) = await get_services(
            view=view,
            db_path_override=db_path,
            index_name_override=index_name,
        )
        await run_quest_flow(
            view=view,
            quest_service=quest_service,
            agent_service=agent_service,
            quest_id=quest_id,
            query_str_arg=query,
            query_file_arg=query_file,
            skip_agent=skip_agent,
        )
    except QuestCliError as e:
        await handle_exception(view, e)
    except FileNotFoundError as e:
        await handle_exception(view, e)
    except Exception as e:
        await handle_exception(view, e)


async def run_quest_flow(
    view: QuestView,
    quest_service: QuestService,
    agent_service: AgentService,
    quest_id: int,
    query_str_arg: str | None,
    query_file_arg: Path | None,
    skip_agent: bool,
):
    quest = quest_service.get_quest(quest_id)
    await view.display_quest_details(quest)
    user_query_str = load_query_from_source(
        query_str=query_str_arg,
        query_file=query_file_arg,
    )
    await view.display_info("\n--- 提出されたクエリ ---")
    await view.display_info(user_query_str)
    (
        is_correct,
        rule_eval_message,
        rule_feedback,
        es_response,
    ) = await quest_service.execute_and_evaluate(quest, user_query_str)
    await view.display_elasticsearch_response(es_response)
    await view.display_evaluation(rule_eval_message, is_correct)
    await view.display_feedback("ルールベース評価フィードバック", rule_feedback)
    agent_feedback = None
    if not skip_agent:
        await view.display_info("\n🤖 LLMエージェントによる評価を実行中...")
        try:
            agent_feedback = await agent_service.run_evaluation_agent(
                quest, user_query_str, rule_eval_message
            )
            await view.display_feedback("🤖 AI評価フィードバック", agent_feedback)
        except QuestCliError as e:
            await view.display_warning(
                f"AI評価中にエラーが発生しました (処理は続行します): {e}"
            )
    if is_correct:
        await view.display_clear_message()
    else:
        await view.display_retry_message()
    await view.close()


def append_message(history, role, content):
    history.append({"role": role, "content": content})
    return history


async def load_quest(quest_id):
    (
        config,
        quest_repo,
        es_client,
        quest_service,
        agent_service,
    ) = await get_services()
    quest = quest_repo.get_quest_by_id(quest_id)
    if quest is None:
        return [
            {"role": "assistant", "content": f"クエストが読み込めません: {quest_id=}"}
        ]
    question = f"""
        ## Quest {quest_id}: {quest.title}
        {quest.description}
        """
    return [{"role": "assistant", "content": question}]


async def submit_answer(quest_id, query, history):
    yield (
        append_message(history, "user", f"これでどう？\n\n{query}"),
        gr.Button(SUBMIT_BUTTON_TEXT, interactive=False),
    )
    view = QueuedQuestView()
    quest_task = asyncio.create_task(cli(quest_id=quest_id, view=view, query=query))
    async for message in view.receive_messages():
        yield (
            append_message(history, "assistant", message),
            gr.Button(SUBMIT_BUTTON_TEXT, interactive=False),
        )
    await quest_task
    yield history, gr.Button(SUBMIT_BUTTON_TEXT, interactive=True, variant="primary")


async def get_mapping(history):
    (
        config,
        quest_repo,
        es_client,
        quest_service,
        agent_service,
    ) = await get_services()
    yield append_message(history, "user", "マッピングを取得して。")
    result = es_client.indices.get_mapping(index=config.index_name)
    formatted_mapping = json.dumps(result.body, indent=4, ensure_ascii=False)
    yield append_message(
        history,
        "assistant",
        f"マッピングは以下のとおりです。\n```json\n{formatted_mapping}\n```",
    )


async def execute_query(query, history):
    (
        config,
        quest_repo,
        es_client,
        quest_service,
        agent_service,
    ) = await get_services()
    try:
        formatted_query = await format_query(query)
    except gr.Error:
        yield append_message(
            history,
            "assistant",
            f"----\nクエリは JSON 形式にしてください:\n```\n{query}\n```",
        )
        return
    yield append_message(
        history,
        "user",
        f"""
        Elasticsearch に直接クエリを投げます。
        ```
        {formatted_query}
        ```
        """,
    )
    result = core_logic_execute_query(es_client, config.index_name, query)
    if len(result["hits"]["hits"]) > 0:
        hits_string = json.dumps(result["hits"]["hits"], indent=4, ensure_ascii=False)
    else:
        hits_string = "ヒット 0 件"
    yield append_message(history, "assistant", f"```\n{hits_string}\n```")


async def init_elasticsearch_index(history):
    (
        config,
        quest_repo,
        es_client,
        quest_service,
        agent_service,
    ) = await get_services()
    yield append_message(history, "user", "Elasticsearch のインデックスを初期化して")
    index_name = config.index_name
    yield append_message(history, "assistant", f"load: {config.book_path}")
    with open(config.book_path, encoding="utf-8") as f:
        data = json.load(f)
    mappings = data["mappings"]
    sample_data = data["sample_data"]
    yield append_message(history, "assistant", "### Elasticsearch の更新")
    yield append_message(history, "assistant", "  - インデックスを削除します")
    es_client.options(ignore_status=[400, 404]).indices.delete(index=index_name)
    yield append_message(history, "assistant", "  - インデックスとマッピングを作成")
    es_client.options(ignore_status=[400]).indices.create(
        index=index_name, body={"mappings": mappings}
    )
    yield append_message(history, "assistant", "  - インデックスにデータを追加")
    actions = []
    for doc_index, doc in enumerate(sample_data):
        if "_index" not in doc:
            doc["_index"] = index_name
            doc["_id"] = doc_index + 1
        actions.append(doc)
    if actions:
        bulk(es_client, actions)
    yield append_message(
        history,
        "assistant",
        f"  - {len(actions)} 件追加\n  - インデックスを再構築しました",
    )


async def format_query(query):
    """
    クエリを整形する
    """
    try:
        query_dict = json.loads(query)
        return json.dumps(query_dict, indent=4, ensure_ascii=False)
    except json.JSONDecodeError:
        raise gr.Error("クエリを整形できません。正しいJSON形式で書いてください。")


async def json_check(query):
    # if query is None or query == "":
    # return JSON_CHECK_NG
    try:
        _ = json.loads(query)
        return JSON_CHECK_OK
    except json.JSONDecodeError:
        return JSON_CHECK_NG
