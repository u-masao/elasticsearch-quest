# src/ui.py (エントリーポイント)
import asyncio
import json
from pathlib import Path
from typing import Any, Dict

import gradio as gr

from src.bootstrap import AppContainer  # DIコンテナを使用する場合

# リファクタリングで分割・作成したモジュールをインポート
from src.config import load_config
from src.exceptions import QuestCliError  # キャッチするベース例外
from src.services.agent_service import AgentService
from src.services.core_logic import execute_query as core_logic_execute_query
from src.services.quest_service import QuestService
from src.utils.query_loader import load_query_from_source
from src.view import EndOfMessage, QuestView

SUBMIT_BUTTON_TEXT = "⭐️ 採点 ⭐️"
JSON_CHECK_OK = "🟢 JSON 形式です"
JSON_CHECK_NG = "❌ JSON 形式？？"


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


# --- ヘルパー関数 ---
async def handle_exception(view: QuestView, e: Exception):
    """集約的な例外ハンドリング"""
    if isinstance(e, QuestCliError):
        # アプリケーション内で定義されたエラー
        await view.display_error(str(e))
    elif isinstance(e, FileNotFoundError):
        # ファイルが見つからない場合のエラーを個別表示
        await view.display_error(f"必要なファイルが見つかりません: {e}")
    else:
        # 予期せぬその他のエラー
        await view.display_error(
            f"予期せぬエラーが発生しました: {type(e).__name__}: {e}"
        )
        # デバッグ用にトレースバックを表示するオプションなど追加しても良い
        # import traceback
        # traceback.print_exc()
    # sys.exit(1)


async def cli(
    view: QueuedQuestView,
    quest_id: int,
    query: str | None = None,
    query_file: Path | None = None,
    db_path: Path | None = None,
    index_name: str | None = None,
    schema_file: Path | None = None,
    data_file: Path | None = None,
    skip_agent: bool = False,
):
    """
    Elasticsearch Quest CLI: 指定されたIDのクエストに挑戦します。

    QUEST_ID: 挑戦するクエストのID（整数）。
    """

    try:
        # 1. 設定のロード (CLI引数でオーバーライド)
        # ValidationError が発生する可能性あり
        config = load_config(
            db_path_override=db_path,
            index_name_override=index_name,
            schema_file_override=schema_file,
            data_file_override=data_file,
        )

        # 2. 依存関係の初期化とサービスの準備
        # DIコンテナを使う場合:
        container = AppContainer(config, view)
        quest_repo = await container.quest_repository  # ここで初期化が走る
        es_client = await container.es_client  # ここで初期化が走る
        quest_service = QuestService(quest_repo, es_client, config.index_name)
        agent_service = AgentService(config, view)  # AgentService も view を使う

        # 3. メイン処理の実行 (非同期)
        await run_quest_flow(
            view=view,
            quest_service=quest_service,
            agent_service=agent_service,
            quest_id=quest_id,
            query_str_arg=query,
            query_file_arg=query_file,
            skip_agent=skip_agent,
        )

    # except ValidationError as e: # Pydantic のエラー
    #     view.display_error(f"設定値が無効です:\n{e}")
    #     sys.exit(1)
    except QuestCliError as e:
        # アプリケーション定義のエラーをまとめて処理
        await handle_exception(view, e)
    except FileNotFoundError as e:
        # クエリファイルが見つからない場合など
        await handle_exception(view, e)
    except Exception as e:  # その他の予期せぬエラー
        await handle_exception(view, e)


# --- 非同期メインフロー ---
async def run_quest_flow(
    view: QuestView,
    quest_service: QuestService,
    agent_service: AgentService,
    quest_id: int,
    query_str_arg: str | None,
    query_file_arg: Path | None,
    skip_agent: bool,
):
    """クエスト実行の非同期フロー"""
    # 1. クエストを取得
    quest = quest_service.get_quest(quest_id)  # QuestNotFoundError が発生する可能性
    await view.display_quest_details(quest)

    # 2. ユーザーのクエリを取得 (ファイル > 文字列 > 対話入力)
    # InvalidQueryError, FileNotFoundError が発生する可能性
    user_query_str = load_query_from_source(
        query_str=query_str_arg,
        query_file=query_file_arg,
        # prompt_func=await view.prompt_for_query
        # if not query_str_arg and not query_file_arg
        # else None,
        # query または query_file が指定されていれば対話入力はしない
    )
    await view.display_info("\n--- 提出されたクエリ ---")
    await view.display_info(user_query_str)  # 提出されたクエリを表示

    # 3. クエリを実行し、ルールベースで評価
    # ElasticsearchError, QuestCliError が発生する可能性
    (
        is_correct,
        rule_eval_message,
        rule_feedback,
        es_response,
    ) = await quest_service.execute_and_evaluate(quest, user_query_str)

    # 4. 結果を表示
    # Elasticsearchレスポンス表示
    await view.display_elasticsearch_response(es_response)
    # ルールベース評価結果表示
    await view.display_evaluation(rule_eval_message, is_correct)
    await view.display_feedback("ルールベース評価フィードバック", rule_feedback)

    # 5. LLMエージェントによる評価 (スキップしない場合)
    agent_feedback = None
    if not skip_agent:
        await view.display_info("\n🤖 LLMエージェントによる評価を実行中...")
        try:
            # AgentError が発生する可能性
            agent_feedback = await agent_service.run_evaluation_agent(
                quest, user_query_str, rule_eval_message
            )
            await view.display_feedback("🤖 AI評価フィードバック", agent_feedback)
        except QuestCliError as e:  # AgentError も QuestCliError を継承
            # エージェント実行中のエラーは警告として表示し、処理は続行する
            await view.display_warning(
                f"AI評価中にエラーが発生しました (処理は続行します): {e}"
            )
        # except Exception as e: # AgentService内で捕捉されなかった予期せぬエラー
        #      view.display_warning(f"AI評価中に予期せぬエラーが発生しました: {e}")

    # 6. 最終結果メッセージ
    if is_correct:
        await view.display_clear_message()
    else:
        await view.display_retry_message()

    # 7. 終了
    await view.close()


async def load_quest(quest_id):
    view = QueuedQuestView()  # View は最初に初期化
    config = load_config()
    container = AppContainer(config, view)
    quest_repo = await container.quest_repository  # ここで初期化が走る
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
    # ユーザーの入力を反映
    history.append({"role": "user", "content": f"これでどう？\n\n{query}"})
    yield history, gr.Button(SUBMIT_BUTTON_TEXT, interactive=False)

    # view を作成
    view = QueuedQuestView()

    # 実行
    quest_task = asyncio.create_task(cli(view=view, quest_id=quest_id, query=query))

    # メッセージを受信
    async for message in view.receive_messages():
        history.append({"role": "assistant", "content": message})
        yield history, gr.Button(SUBMIT_BUTTON_TEXT, interactive=False)

    # タスク完了までブロック
    await quest_task

    # タスク完了時にボタンを有効化
    yield history, gr.Button(SUBMIT_BUTTON_TEXT, interactive=True, variant="primary")


def json_check(query):
    if query is None or query == "":
        return JSON_CHECK_NG
    try:
        _ = json.loads(query)
        return JSON_CHECK_OK
    except json.JSONDecodeError:
        return JSON_CHECK_NG


async def get_mapping(history):
    history.append(
        {
            "role": "user",
            "content": "マッピングを取得して。",
        }
    )
    yield history

    view = QueuedQuestView()
    config = load_config()
    container = AppContainer(config, view)
    es_client = await container.es_client

    result = es_client.indices.get_mapping(index=config.index_name)
    formatted_mapping = json.dumps(result.body, indent=4, ensure_ascii=False)
    history.append(
        {
            "role": "assistant",
            "content": "マッピングは以下のとおりです。\n"
            f"```json\n{formatted_mapping}\n```",
        }
    )
    yield history


async def execute_query(query, history):
    print(f"query: {query}")
    try:
        formatted_query = json.dumps(json.loads(query), indent=4, ensure_ascii=False)
    except json.JSONDecodeError:
        history.append(
            {
                "role": "assistant",
                "content": "----\nクエリは JSON 形式にしてください:\n"
                f"```\n{query}\n```",
            }
        )
        yield history
        return

    history.append(
        {
            "role": "user",
            "content": f"""
        Elasticsearch に直接クエリを投げます。
        ```
        {formatted_query}
        ```
        """,
        }
    )
    yield history

    view = QueuedQuestView()
    config = load_config()
    container = AppContainer(config, view)
    es_client = await container.es_client
    result = core_logic_execute_query(es_client, config.index_name, query)
    if len(result["hits"]["hits"]) > 0:
        hits_string = json.dumps(result["hits"]["hits"], indent=4, ensure_ascii=False)
    else:
        hits_string = "ヒット 0 件"

    history.append({"role": "assistant", "content": f"```\n{hits_string}\n```"})
    yield history


def format_query(query):
    query_dict = json.loads(query)
    return json.dumps(query_dict, indent=4, ensure_ascii=False)


with gr.Blocks(fill_width=True, fill_height=True) as demo:
    with gr.Row(equal_height=True, scale=1):
        with gr.Column(scale=2):
            ui_chat = gr.Chatbot(type="messages")
        with gr.Column(scale=1):
            ui_user_query = gr.Textbox(
                "{}",
                lines=20,
                label="JSON形式でクエリを書いて「採点」ボタンを押してください",
                scale=5,
            )
            with gr.Column():
                ui_quest_id = gr.Number(1, label="クエストID選択")
                ui_json_validator = gr.Markdown(JSON_CHECK_OK)
                ui_execute_button = gr.Button("▶️  テスト実行 ▶️", variant="secondary")
                ui_format_button = gr.Button("✨ 自動整形 ✨")
                ui_mapping_button = gr.Button("マッピング取得")
                ui_submit_button = gr.Button(SUBMIT_BUTTON_TEXT, variant="primary")

    # select quest
    ui_user_query.change(
        json_check, inputs=[ui_user_query], outputs=[ui_json_validator]
    )

    # load quest
    gr.on(
        [ui_quest_id.change],
        fn=load_quest,
        inputs=[ui_quest_id],
        outputs=[ui_chat],
    )

    # submit query
    ui_submit_button.click(
        submit_answer,
        inputs=[ui_quest_id, ui_user_query, ui_chat],
        outputs=[ui_chat, ui_submit_button],
    )

    # execute query
    gr.on(
        [ui_execute_button.click],
        fn=execute_query,
        inputs=[ui_user_query, ui_chat],
        outputs=[ui_chat],
    )

    # format query
    gr.on(
        [ui_format_button.click],
        fn=format_query,
        inputs=[ui_user_query],
        outputs=[ui_user_query],
    )

    # get mapping
    gr.on(
        [ui_mapping_button.click],
        fn=get_mapping,
        inputs=[ui_chat],
        outputs=[ui_chat],
    )


if __name__ == "__main__":
    demo.launch(share=False, debug=True)
