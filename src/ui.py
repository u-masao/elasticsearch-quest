# src/ui.py (エントリーポイント)
import asyncio
import json
from pathlib import Path

import gradio as gr

from src.bootstrap import AppContainer  # DIコンテナを使用する場合

# リファクタリングで分割・作成したモジュールをインポート
from src.config import (  # デフォルト値表示用
    load_config,
)
from src.exceptions import QuestCliError  # キャッチするベース例外
from src.services.agent_service import AgentService

# または個別にインポート: from .bootstrap import initialize_database, initialize_elasticsearch
from src.services.quest_service import QuestService
from src.utils.query_loader import load_query_from_source
from src.view import QuestView


# --- ヘルパー関数 ---
def handle_exception(view: QuestView, e: Exception):
    """集約的な例外ハンドリング"""
    if isinstance(e, QuestCliError):
        # アプリケーション内で定義されたエラー
        view.display_error(str(e))
    elif isinstance(e, FileNotFoundError):
        # ファイルが見つからない場合のエラーを個別表示
        view.display_error(f"必要なファイルが見つかりません: {e}")
    else:
        # 予期せぬその他のエラー
        view.display_error(f"予期せぬエラーが発生しました: {type(e).__name__}: {e}")
        # デバッグ用にトレースバックを表示するオプションなど追加しても良い
        # import traceback
        # traceback.print_exc()
    # sys.exit(1)


def cli(
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
    view = QuestView()  # View は最初に初期化

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
        quest_repo = container.quest_repository  # ここで初期化が走る
        es_client = container.es_client  # ここで初期化が走る
        quest_service = QuestService(quest_repo, es_client, config.index_name)
        agent_service = AgentService(config, view)  # AgentService も view を使う

        # DIコンテナを使わない場合:
        # quest_repo = initialize_database(config, view)
        # es_client = initialize_elasticsearch(config, view)
        # quest_service = QuestService(quest_repo, es_client, config.index_name)
        # agent_service = AgentService(config, view)

        # 3. メイン処理の実行 (非同期)
        asyncio.run(
            run_quest_flow(
                view=view,
                quest_service=quest_service,
                agent_service=agent_service,
                quest_id=quest_id,
                query_str_arg=query,
                query_file_arg=query_file,
                skip_agent=skip_agent,
            )
        )

    # except ValidationError as e: # Pydantic のエラー
    #     view.display_error(f"設定値が無効です:\n{e}")
    #     sys.exit(1)
    except QuestCliError as e:
        # アプリケーション定義のエラーをまとめて処理
        handle_exception(view, e)
    except FileNotFoundError as e:
        # クエリファイルが見つからない場合など
        handle_exception(view, e)
    except Exception as e:  # その他の予期せぬエラー
        handle_exception(view, e)


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
    view.display_quest_details(quest)

    # 2. ユーザーのクエリを取得 (ファイル > 文字列 > 対話入力)
    # InvalidQueryError, FileNotFoundError が発生する可能性
    user_query_str = load_query_from_source(
        query_str=query_str_arg,
        query_file=query_file_arg,
        prompt_func=view.prompt_for_query
        if not query_str_arg and not query_file_arg
        else None,
        # query または query_file が指定されていれば対話入力はしない
    )
    view.display_info("\n--- 提出されたクエリ ---")
    view.display_info(user_query_str)  # 提出されたクエリを表示

    # 3. クエリを実行し、ルールベースで評価
    # ElasticsearchError, QuestCliError が発生する可能性
    is_correct, rule_eval_message, rule_feedback, es_response = (
        quest_service.execute_and_evaluate(quest, user_query_str)
    )

    # 4. 結果を表示
    # Elasticsearchレスポンス表示
    view.display_elasticsearch_response(es_response)
    # ルールベース評価結果表示
    view.display_evaluation(rule_eval_message, is_correct)
    view.display_feedback("ルールベース評価フィードバック", rule_feedback)

    # 5. LLMエージェントによる評価 (スキップしない場合)
    agent_feedback = None
    if not skip_agent:
        view.display_info("\n🤖 LLMエージェントによる評価を実行中...")
        try:
            # AgentError が発生する可能性
            agent_feedback = await agent_service.run_evaluation_agent(
                quest, user_query_str, rule_eval_message
            )
            view.display_feedback("🤖 AI評価フィードバック", agent_feedback)
        except QuestCliError as e:  # AgentError も QuestCliError を継承
            # エージェント実行中のエラーは警告として表示し、処理は続行する
            view.display_warning(
                f"AI評価中にエラーが発生しました (処理は続行します): {e}"
            )
        # except Exception as e: # AgentService内で捕捉されなかった予期せぬエラー
        #      view.display_warning(f"AI評価中に予期せぬエラーが発生しました: {e}")

    # 6. 最終結果メッセージ
    if is_correct:
        view.display_clear_message()
    else:
        view.display_retry_message()


def load_quest(quest_id):
    view = QuestView()  # View は最初に初期化
    config = load_config()
    container = AppContainer(config, view)
    quest_repo = container.quest_repository  # ここで初期化が走る
    quest = quest_repo.get_quest_by_id(quest_id)
    if quest is None:
        return gr.Markdown("")
    question = f"""
        quest_id={quest_id} name フィールドに 
        "Deep Learning" で部分一致するクエリを書いて

        ## {quest.title}

        {quest.description}

        ## detail
        {quest}
        """
    return gr.Markdown(question)


def submit_answer(quest_id, query, history):
    history.append({"role": "user", "content": f"これでどう？\n\n{query}"})
    cli(quest_id=quest_id, query=query)
    correct = '{"query": {"match": {"name": "Hello"}}}'
    response = f"""
    あなたのクエリは {query} です。
    クエスト {quest_id} の正解は

    ```json
    {correct}
    ```
    でした。

    正解おめでとうございます🤖 
    """
    history.append({"role": "assistant", "content": response})
    return history


def json_check(query):
    if query is None or query == "":
        return "🟥 JSON 形式ではありません"
    try:
        _ = json.loads(query)
        return "🟩 JSON 形式です"
    except json.JSONDecodeError:
        return "🟥 JSON 形式ではありません"


with gr.Blocks() as demo:
    ui_quest_id = gr.Number(1)
    ui_question_markdown = gr.Markdown()
    ui_user_query = gr.Textbox("", lines=5, label="ここに答えを書いてください")
    ui_json_validator = gr.Markdown()
    ui_submit_button = gr.Button("submit")
    ui_chat = gr.Chatbot(type="messages")

    ui_user_query.change(
        json_check, inputs=[ui_user_query], outputs=[ui_json_validator]
    )
    gr.on(
        [demo.load, ui_quest_id.change],
        fn=load_quest,
        inputs=[ui_quest_id],
        outputs=[ui_question_markdown],
    )
    ui_submit_button.click(
        submit_answer,
        inputs=[ui_quest_id, ui_user_query, ui_chat],
        outputs=[ui_chat],
    )


if __name__ == "__main__":
    demo.launch(share=False, debug=True)
