# src/cli.py
import os
import json
from pathlib import Path
import sys
import click
from elasticsearch import TransportError

# --- 設定 (Config) ---
# プロジェクトルートをパスに追加（srcなどをインポートするため）
# このファイルが src/cli.py にある想定
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# --- データアクセス層 (Model/Repository) & コアロジック ---
try:
    from src.db.quest_repository import QuestRepository, Quest  # Questもインポート
    from src.elasticsearch_client import get_es_client
    from src.core_logic import (
        execute_query,
        evaluate_result,
        get_feedback,
    )
except ImportError as e:
    print(f"必要なモジュールのインポートに失敗しました: {e}", file=sys.stderr)
    print(
        "プロジェクト構造を確認するか、必要なライブラリをインストールしてください。",
        file=sys.stderr,
    )
    sys.exit(1)

# --- 設定値 (Config) ---
DB_FILE_PATH_DEFAULT = project_root / "data/quests.db"
INDEX_NAME_DEFAULT = "sample_books"
FIXTURES_DIR_DEFAULT = project_root / "fixtures"
SCHEMA_FILE_DEFAULT = FIXTURES_DIR_DEFAULT / "create_quests_table.sql"
DATA_FILE_DEFAULT = FIXTURES_DIR_DEFAULT / "insert_quests.sql"


# --- ビュー層 (View) ---
class QuestView:
    """CLIへの出力を担当するクラス"""

    def display_quest_details(self, quest: Quest):
        """クエストの詳細情報を表示する"""
        title_line = f"--- クエスト {quest.quest_id}: {quest.title} ---"
        click.echo(click.style(title_line, fg="cyan", bold=True))
        click.echo(f"難易度: {quest.difficulty}")
        click.echo(f"内容: {quest.description}")
        click.echo("-" * len(title_line))

    def display_elasticsearch_response(self, response: dict):
        """Elasticsearchからのレスポンス（一部）を表示する"""
        click.echo(click.style("\n--- Elasticsearch Response (Hits) ---", bold=True))
        hits_info = response.get("hits", {})
        total_hits = hits_info.get("total", {}).get("value", "N/A")
        click.echo(f"Total Hits: {total_hits}")

        hits = hits_info.get("hits", [])
        if hits:
            click.echo("Documents (first few):")
            for i, hit in enumerate(hits[:3]):  # 上位3件表示
                source_name = hit.get("_source", {}).get("name", "N/A")
                isbn = hit.get("_source", {}).get("isbn", "N/A")
                click.echo(
                    f"  {i + 1}. ID: {click.style(str(hit.get('_id')), fg='yellow')}, "
                    f"ISBN: {click.style(isbn, fg='yellow')}, "
                    f"Score: {click.style(str(hit.get('_score')), fg='blue')}, "
                    f"Source Name: {source_name}"
                )
        else:
            click.echo("Documents: (No hits)")

        if "aggregations" in response:
            click.echo(
                click.style(
                    "\n--- Elasticsearch Response (Aggregations) ---", bold=True
                )
            )
            click.echo(
                json.dumps(response["aggregations"], indent=2, ensure_ascii=False)
            )
        click.echo("-" * 30)

    def display_evaluation(self, message: str, is_correct: bool):
        """評価結果を表示する"""
        click.echo(click.style("\n--- 評価 ---", bold=True))
        color = "green" if is_correct else "red"
        click.echo(click.style(message, fg=color))
        click.echo("-" * 12)

    def display_feedback(self, feedback: str | None):
        """フィードバックを表示する"""
        if feedback:
            click.echo(click.style("\n--- フィードバック ---", bold=True))
            click.echo(feedback)
            click.echo("-" * 18)

    def display_error(self, message: str):
        """汎用エラーメッセージを表示する"""
        click.secho(f"エラー: {message}", fg="red", err=True)

    def display_query_execution_error(self, error: Exception):
        """クエリ実行時エラーと評価を表示する"""
        click.secho(f"\nクエリエラー: {error}", fg="red", err=True)
        click.echo(click.style("\n--- 評価 ---", bold=True))
        click.echo(
            click.style("不正解... クエリの実行中にエラーが発生しました。", fg="red")
        )
        click.echo("-" * 12)

    def display_warning(self, message: str):
        """警告メッセージを表示する"""
        click.secho(f"警告: {message}", fg="yellow", err=True)

    def display_clear_message(self):
        """クエストクリアメッセージを表示する"""
        click.secho("\nクエストクリア！おめでとうございます！", fg="green", bold=True)

    def display_retry_message(self):
        """再挑戦を促すメッセージ（現状は空）"""
        pass  # 必要に応じてメッセージを追加

    def prompt_for_query(self) -> str:
        """対話的にクエリ入力を求める"""
        click.echo(
            click.style(
                "\nElasticsearchクエリをJSON形式で入力してください (Ctrl+D or Ctrl+Z+Enter で終了):",
                fg="blue",
            )
        )
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        return "\n".join(lines)


# --- コントローラー層 (Logic) ---
class QuestController:
    """アプリケーションのロジックを担当するクラス"""

    def __init__(
        self, db_path: Path, index_name: str, schema_file: Path, data_file: Path
    ):
        self.db_path = db_path
        self.index_name = index_name
        self.schema_file = schema_file
        self.data_file = data_file
        self.view = QuestView()
        self.quest_repo: QuestRepository | None = None
        self.es_client = None

    def _initialize_dependencies(self):
        """データベースとElasticsearchクライアントを初期化する"""
        self._initialize_db()
        self._initialize_es_client()

    def _initialize_db(self):
        """データベースリポジトリを初期化し、必要であればスキーマとデータをロードする"""
        try:
            # DBファイルパスの親ディレクトリが存在しない場合は作成
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.quest_repo = QuestRepository(str(self.db_path))
            if not self.db_path.exists() or self.db_path.stat().st_size == 0:
                click.echo(
                    f"データベースファイル '{self.db_path}' が存在しないか空です。初期化します..."
                )
                if not self.schema_file.exists():
                    raise FileNotFoundError(
                        f"スキーマファイルが見つかりません: {self.schema_file}"
                    )
                if not self.data_file.exists():
                    raise FileNotFoundError(
                        f"データファイルが見つかりません: {self.data_file}"
                    )
                self.quest_repo.initialize_schema(str(self.schema_file))
                self.quest_repo.load_data(str(self.data_file))
                click.echo("データベースの初期化が完了しました。")
        except Exception as e:
            self.view.display_error(f"データベース初期化中にエラーが発生しました: {e}")
            sys.exit(1)

    def _initialize_es_client(self):
        """Elasticsearchクライアントを初期化する"""
        try:
            self.es_client = get_es_client()
            if not self.es_client.ping():
                self.view.display_error(
                    "Elasticsearch に接続できません。ping() が Falseを返しました"
                )
                sys.exit(1)
        except Exception as e:
            self.view.display_error(
                f"Elasticsearchクライアントの初期化中に予期せぬエラーが発生しました: {e}"
            )
            sys.exit(1)

    def _get_quest(self, quest_id: int) -> Quest:
        """指定されたIDのクエストを取得する"""
        if not self.quest_repo:
            raise RuntimeError(
                "QuestRepositoryが初期化されていません。"
            )  # 事前チェック
        quest = self.quest_repo.get_quest_by_id(quest_id)
        if not quest:
            self.view.display_error(f"クエストID {quest_id} が見つかりません。")
            sys.exit(1)
        return quest

    def _get_user_query(self, query_str: str | None, query_file: str | None) -> str:
        """ユーザーが指定したクエリ文字列を取得する (ファイル > 文字列 > 対話入力)"""
        user_query = None
        if query_file:
            try:
                user_query = Path(query_file).read_text(encoding="utf-8")
            except FileNotFoundError:
                self.view.display_error(f"クエリファイルが見つかりません: {query_file}")
                sys.exit(1)
            except Exception as e:
                self.view.display_error(
                    f"クエリファイルの読み込みに失敗しました ({query_file}): {e}"
                )
                sys.exit(1)
        elif query_str:
            user_query = query_str
        else:
            user_query = self.view.prompt_for_query()

        if not user_query or not user_query.strip():
            self.view.display_error("実行するクエリが指定または入力されませんでした。")
            sys.exit(1)

        # 簡単なJSON形式チェック (より厳密なチェックは core_logic.execute_query に任せる)
        try:
            json.loads(user_query)
        except json.JSONDecodeError as e:
            self.view.display_warning(
                f"入力されたクエリが有効なJSON形式ではない可能性があります: {e}"
            )
            # 続行させるか、ここで終了させるかは要件次第
            # sys.exit(1)

        return user_query

    def _execute_and_evaluate(
        self, quest: Quest, user_query_str: str
    ) -> tuple[bool, str, str | None]:
        """クエリを実行し、結果を評価してフィードバックを得る"""
        attempt_count = 1  # 仮実装 (将来的に試行回数を管理する場合は変更)
        is_correct = False
        eval_message = "評価エラー"
        feedback = None
        es_response = None

        try:
            if not self.es_client:
                raise RuntimeError(
                    "Elasticsearch clientが初期化されていません。"
                )  # 事前チェック
            es_response = execute_query(self.es_client, self.index_name, user_query_str)
            self.view.display_elasticsearch_response(es_response)
            is_correct, eval_message = evaluate_result(quest, es_response)
            feedback = get_feedback(quest, is_correct, attempt_count)
        except (ValueError, TransportError, json.JSONDecodeError) as e:
            # クエリ実行/パース時のエラー
            self.view.display_query_execution_error(e)
            # エラー時の評価とフィードバック
            is_correct = False
            # eval_message は display_query_execution_error 内で表示されるため不要
            feedback = get_feedback(
                quest, is_correct=False, attempt_count=attempt_count
            )
            # この関数は評価結果とフィードバックを返す責務を持つため、エラーの場合も値を設定する
            eval_message = "不正解... クエリの実行中にエラーが発生しました。"  # 呼び出し元での評価表示用
        except Exception as e:
            # 予期せぬエラー
            self.view.display_error(
                f"クエリ実行または評価中に予期せぬエラーが発生しました: {e}"
            )
            sys.exit(1)  # 予期せぬエラーは処理中断

        return is_correct, eval_message, feedback

    def run_quest(self, quest_id: int, query_str: str | None, query_file: str | None):
        """クエスト実行のメインフロー"""
        self._initialize_dependencies()

        quest = self._get_quest(quest_id)
        self.view.display_quest_details(quest)

        user_query = self._get_user_query(query_str, query_file)

        is_correct, eval_message, feedback = self._execute_and_evaluate(
            quest, user_query
        )

        # クエリエラーの場合、評価メッセージは _execute_and_evaluate 内で表示済み
        if eval_message != "不正解... クエリの実行中にエラーが発生しました。":
            self.view.display_evaluation(eval_message, is_correct)

        self.view.display_feedback(feedback)

        if is_correct:
            self.view.display_clear_message()
        else:
            self.view.display_retry_message()


# --- CLIエントリーポイント ---
def check_env_vars():
    """Elasticsearch接続に必要な環境変数の存在を確認し、警告を表示する"""
    if "ELASTICSEARCH_URL" not in os.environ and "ELASTIC_CLOUD_ID" not in os.environ:
        QuestView().display_warning(
            "環境変数 ELASTICSEARCH_URL または ELASTIC_CLOUD_ID が設定されていません。\n"
            "デフォルトの http://localhost:9200 に接続を試みます。"
        )


@click.command()
@click.argument("quest_id", type=int)
@click.option(
    "--query", "-q", type=str, help="実行するElasticsearchクエリ (JSON文字列)"
)
@click.option(
    "--query_file",  # <- 変更
    "-f",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="実行するElasticsearchクエリが書かれたJSONファイルパス",
)
@click.option(
    "--db_path",  # <- 変更
    type=click.Path(
        dir_okay=False, writable=True, path_type=Path
    ),  # 書き込み可能かチェック
    default=DB_FILE_PATH_DEFAULT,
    help="クエストDBファイルのパス",
    envvar="QUEST_DB_PATH",
    show_default=True,
)
@click.option(
    "--index_name",  # <- 変更
    type=str,
    default=INDEX_NAME_DEFAULT,
    help="Elasticsearchインデックス名",
    envvar="ES_INDEX_NAME",
    show_default=True,
)
@click.option(
    "--schema_file",  # <- 変更
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=SCHEMA_FILE_DEFAULT,
    help="DBスキーマSQLファイルパス",
    show_default=True,
)
@click.option(
    "--data_file",  # <- 変更
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DATA_FILE_DEFAULT,
    help="DB初期データSQLファイルパス",
    show_default=True,
)
# @click.option("--show_solution", is_flag=True, help="指定したクエストの解答例を表示する") # TODO: 解答例機能実装時に有効化 (これも変更)
def cli(
    quest_id: int,
    query: str | None,
    query_file: Path | None,
    db_path: Path,
    index_name: str,
    schema_file: Path,
    data_file: Path,
):
    """
    Elasticsearch Quest CLI: 指定されたIDのクエストに挑戦します。

    QUEST_ID: 挑戦するクエストのID（整数）。
    """
    check_env_vars()

    # if show_solution: # TODO: 解答例機能
    #     # controller = QuestController(...) # 初期化が必要な場合
    #     # controller.show_solution(quest_id)
    #     sys.exit(0)

    controller = QuestController(
        db_path=db_path,
        index_name=index_name,
        schema_file=schema_file,
        data_file=data_file,
    )
    controller.run_quest(
        quest_id=quest_id,
        query_str=query,
        # click.Path(path_type=Path) を使っているので、query_file は Path オブジェクト
        query_file=str(query_file) if query_file else None,
    )


if __name__ == "__main__":
    cli()
