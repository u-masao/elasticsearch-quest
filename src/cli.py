# src/cli.py (エントリーポイント)
import asyncio
import sys
from pathlib import Path

import click

from .bootstrap import AppContainer  # DIコンテナを使用する場合

# リファクタリングで分割・作成したモジュールをインポート
from .config import (  # デフォルト値表示用
    DEFAULT_DATA_FILE,
    DEFAULT_DB_FILE_PATH,
    DEFAULT_INDEX_NAME,
    DEFAULT_SCHEMA_FILE,
    load_config,
)
from .exceptions import QuestCliError  # キャッチするベース例外
from .services.agent_service import AgentService

# または個別にインポート: from .bootstrap import initialize_database, initialize_elasticsearch
from .services.quest_service import QuestService
from .utils.query_loader import load_query_from_source
from .view import QuestView


# --- ヘルパー関数 ---
def handle_exception(view: QuestView, e: Exception):
    """集約的な例外ハンドリング"""
    if isinstance(e, QuestCliError):
        # アプリケーション内で定義されたエラー
        view.display_error(str(e))
    elif isinstance(e, FileNotFoundError):
        # ファイルが見つからない場合のエラーを個別表示
        view.display_error(f"必要なファイルが見つかりません: {e}")
    elif isinstance(e, click.ClickException):
        # Clickライブラリ自身のエラー (例: 不正なオプション)
        e.show()  # Clickのデフォルトエラー表示
    else:
        # 予期せぬその他のエラー
        view.display_error(f"予期せぬエラーが発生しました: {type(e).__name__}: {e}")
        # デバッグ用にトレースバックを表示するオプションなど追加しても良い
        # import traceback
        # traceback.print_exc()
    sys.exit(1)


# --- CLIコマンド本体 ---
@click.command()
@click.argument("quest_id", type=int)
@click.option(
    "--query",
    "-q",
    type=str,
    help="実行するElasticsearchクエリ (JSON文字列)。ファイルと両方指定された場合はこちらが優先。",
)
@click.option(
    "--query_file",
    "-f",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="実行するElasticsearchクエリが書かれたJSONファイルパス。",
)
# --- 設定オプション (config.py のデフォルト値を上書き) ---
# show_default=True にするとヘルプ表示が長くなるため、デフォルト値は help 文字列内に記述
@click.option(
    "--db_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    help=f"クエストDBファイルのパス (デフォルト: {DEFAULT_DB_FILE_PATH})",
)
@click.option(
    "--index_name",
    type=str,
    help=f"Elasticsearchインデックス名 (デフォルト: {DEFAULT_INDEX_NAME})",
)
@click.option(
    "--schema_file",
    type=click.Path(
        exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path
    ),
    help=f"DBスキーマSQLファイルパス (デフォルト: {DEFAULT_SCHEMA_FILE})",
)
@click.option(
    "--data_file",
    type=click.Path(
        exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path
    ),
    help=f"DB初期データSQLファイルパス (デフォルト: {DEFAULT_DATA_FILE})",
)
@click.option(
    "--skip_agent",
    is_flag=True,
    default=False,
    help="LLMエージェントによる評価をスキップする。",
)
# @click.option("--show_solution", is_flag=True, help="指定したクエストの解答例を表示する") # TODO

def cli(
    quest_id: int,
    query: str | None,
    query_file: Path | None,
    db_path: Path | None,
    index_name: str | None,
    schema_file: Path | None,
    data_file: Path | None,
    skip_agent: bool,
    # show_solution: bool, # TODO
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
    except click.ClickException as e:
        # Click関連のエラー
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
    click.echo(user_query_str)  # 提出されたクエリを表示

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


# --- エントリーポイント ---
if __name__ == "__main__":
    # `python -m src.cli ...` で実行することを推奨
    cli()
