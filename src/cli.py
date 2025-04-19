# src/cli.py (修正済みコード全体 - 2025-04-14)
import asyncio
import sys
import traceback  # traceback をインポート
from pathlib import Path

import click

from .bootstrap import AppContainer  # DIコンテナ
from .config import (  # 設定関連
    DEFAULT_DATA_FILE,
    DEFAULT_DB_FILE_PATH,
    DEFAULT_INDEX_NAME,
    DEFAULT_SCHEMA_FILE,
    load_config,
)
from .exceptions import QuestCliError  # アプリケーション例外
from .services.agent_service import AgentService  # サービス
from .services.quest_service import QuestService  # サービス
from .utils.query_loader import load_query_from_source  # クエリローダー
from .view import QuestView  # View


# --- ヘルパー関数 (エラーハンドリング) ---
async def handle_exception(view: QuestView, e: Exception):
    """集約的な例外ハンドリング (非同期)"""
    if isinstance(e, QuestCliError):
        await view.display_error(str(e))
    elif isinstance(e, FileNotFoundError):
        await view.display_error(f"必要なファイルが見つかりません: {e}")
    elif isinstance(e, click.ClickException):
        e.show()
    else:
        await view.display_error(
            f"予期せぬエラーが発生しました: {type(e).__name__}: {e}"
        )
        # エラー詳細が必要な場合はトレースバックを表示
        click.echo("\n--- Traceback ---", err=True)
        traceback.print_exc()
    sys.exit(1)  # エラーハンドリング後は終了


# --- 非同期メインフロー (クエスト実行ロジック) ---
# (この関数の内部実装は前の版から変更なし、ただし呼び出し元で渡される
#  quest_service, agent_service が正しく初期化されていることが前提)
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
    # 1. クエストを取得 (QuestService 内部でリポジトリ使用)
    quest = quest_service.get_quest(quest_id)
    await view.display_quest_details(quest)

    # 2. ユーザーのクエリを取得
    user_query_str = load_query_from_source(
        query_str=query_str_arg,
        query_file=query_file_arg,
        # prompt_func=await view.prompt_for_query
        # if not query_str_arg and not query_file_arg
        # else None,
    )
    await view.display_info("\n--- 提出されたクエリ ---")
    click.echo(user_query_str)

    # 3. クエリを実行し、ルールベースで評価 (QuestService 内部で ES クライアント使用)
    (
        is_correct,
        rule_eval_message,
        rule_feedback,
        es_response,
    ) = await quest_service.execute_and_evaluate(quest, user_query_str)

    # 4. 結果を表示
    await view.display_elasticsearch_response(es_response)
    await view.display_evaluation(rule_eval_message, is_correct)
    await view.display_feedback("ルールベース評価フィードバック", rule_feedback)

    # 5. LLMエージェントによる評価
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
        except Exception as e:
            await view.display_warning(f"AI評価中に予期せぬエラーが発生しました: {e}")

    # 6. 最終結果メッセージ
    if is_correct:
        await view.display_clear_message()
    else:
        await view.display_retry_message()


# --- 非同期処理のラッパー (初期化と例外処理担当) ---
async def main_wrapper(
    config: dict,  # config を受け取る
    view: QuestView,  # view を受け取る
    quest_id: int,
    query_str_arg: str | None,
    query_file_arg: Path | None,
    skip_agent: bool,
):
    """非同期の初期化、実行、例外処理を行う"""
    container = None  # エラーハンドリング用に初期化
    try:
        # --- DIコンテナの初期化 ---
        container = AppContainer(config, view)

        # --- 非同期な依存関係の取得 ---
        # 【重要】AppContainerの実装に合わせて await の形式を確認・修正してください
        # 例: async def quest_repository(self): -> await container.quest_repository()
        # 例: @property async def quest_repository(self):
        #       -> await container.quest_repository
        quest_repo = await container.quest_repository()
        es_client = await container.es_client()

        # --- サービスのインスタンス化 ---
        quest_service = QuestService(quest_repo, es_client, config.index_name)
        agent_service = AgentService(config, view)

        # --- メインの非同期フローを実行 ---
        await run_quest_flow(
            view=view,
            quest_service=quest_service,
            agent_service=agent_service,
            quest_id=quest_id,
            query_str_arg=query_str_arg,
            query_file_arg=query_file_arg,
            skip_agent=skip_agent,
        )

    except (QuestCliError, FileNotFoundError) as e:
        # アプリケーション定義のエラーやファイル関連エラー
        # view が初期化されていれば非同期ハンドラへ
        if view:
            await handle_exception(view, e)
        else:
            click.echo(f"初期化中のエラー: {e}", err=True)  # view がない場合
            sys.exit(1)

    except Exception as e:
        # その他の予期せぬエラー
        if view:
            await handle_exception(view, e)
        else:
            click.echo(f"初期化中の予期せぬエラー: {type(e).__name__}: {e}", err=True)
            traceback.print_exc()
            sys.exit(1)


# --- CLIコマンド本体 (エントリーポイント、同期処理担当) ---
@click.command()
@click.argument("quest_id", type=int)
@click.option(
    "--query",
    "-q",
    type=str,
    help="実行するElasticsearchクエリ (JSON文字列)。"
    "ファイルと両方指定された場合はこちらが優先。",
)
@click.option(
    "--query_file",
    "-f",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="実行するElasticsearchクエリが書かれたJSONファイルパス。",
)
# --- 設定オプション ---
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
def cli(
    quest_id: int,
    query: str | None,
    query_file: Path | None,
    db_path: Path | None,
    index_name: str | None,
    schema_file: Path | None,
    data_file: Path | None,
    skip_agent: bool,
):
    """
    Elasticsearch Quest CLI: 指定されたIDのクエストに挑戦します。

    QUEST_ID: 挑戦するクエストのID（整数）。
    """
    # View は最初に同期的に初期化
    # (非同期処理内でエラーが出ても最低限の表示はできるように)
    view = QuestView()

    try:
        # 1. 設定のロード (同期処理)
        # ここで ValidationError などが発生する可能性あり
        config = load_config(
            db_path_override=db_path,
            index_name_override=index_name,
            schema_file_override=schema_file,
            data_file_override=data_file,
        )

        # 2. 非同期処理の実行 (初期化は main_wrapper 内で行う)
        # asyncio.run は、内部 (main_wrapper) で捕捉されなかった例外を再送出する
        asyncio.run(
            main_wrapper(
                config=config,  # 作成した config を渡す
                view=view,  # 作成した view を渡す
                quest_id=quest_id,
                query_str_arg=query,
                query_file_arg=query_file,
                skip_agent=skip_agent,
            )
        )

    except click.ClickException as e:
        # Clickライブラリ自身の引数/オプションエラー
        e.show()
        sys.exit(1)
    except QuestCliError as e:
        # config ロード中のアプリ固有エラーなど、asyncio.run の前のエラー
        click.echo(f"設定エラー: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        # config ロード中など、asyncio.run の前の予期せぬ同期エラー
        # または asyncio.run から送出された (main_wrapperで捕捉されなかった) エラー
        click.echo(
            f"予期せぬエラーが発生しました (同期コンテキスト): {type(e).__name__}: {e}",
            err=True,
        )
        traceback.print_exc()  # トレースバック表示
        sys.exit(1)


# --- エントリーポイント ---
if __name__ == "__main__":
    # `python -m src.cli ...` または `uv run python -m src.cli ...` で実行
    cli()
