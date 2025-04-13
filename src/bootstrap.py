# src/bootstrap.py
from elasticsearch import Elasticsearch

from .config import AppConfig
from .db.quest_repository import QuestRepository
from .es.client import get_es_client  # 実装は後述
from .exceptions import DatabaseError, ElasticsearchError
from .view import QuestView


def initialize_database(config: AppConfig, view: QuestView) -> QuestRepository:
    """
    データベースリポジトリを初期化し、必要であればスキーマとデータをロードする。

    Args:
        config: アプリケーション設定オブジェクト.
        view: CLI表示用オブジェクト.

    Returns:
        初期化されたQuestRepositoryインスタンス.

    Raises:
        DatabaseError: データベースの初期化や接続に失敗した場合.
    """
    try:
        repo = QuestRepository(str(config.db_path))

        # DBファイルが存在しないか空の場合、初期化処理を実行
        # ファイルの存在チェックは config の FilePath Validator が行う
        # ここではファイルサイズで空かどうかをチェック
        if not config.db_path.exists() or config.db_path.stat().st_size == 0:
            view.display_info(
                f"データベースファイル '{config.db_path}' が存在しないか空のため初期化します..."
            )
            repo.initialize_schema(str(config.schema_file))
            repo.load_data(str(config.data_file))
            view.display_info("データベースの初期化が完了しました。")
        else:
            view.display_info(f"データベース '{config.db_path}' を使用します。")
        return repo
    except Exception as e:
        # QuestRepository 内で発生したエラーも含む
        raise DatabaseError(f"データベース初期化中にエラーが発生しました: {e}") from e


def initialize_elasticsearch(config: AppConfig, view: QuestView) -> Elasticsearch:
    """
    Elasticsearchクライアントを初期化し、接続を確認する。

    Args:
        config: アプリケーション設定オブジェクト.
        view: CLI表示用オブジェクト.

    Returns:
        初期化されたElasticsearchクライアントインスタンス.

    Raises:
        ElasticsearchError: Elasticsearchへの接続やクライアント初期化に失敗した場合.
    """
    try:
        # 環境変数に関する警告 (接続情報がない場合)
        if not config.elasticsearch_url and not config.elastic_cloud_id:
            view.display_warning(
                "環境変数 ELASTICSEARCH_URL または ELASTIC_CLOUD_ID が設定されていません。\n"
                "デフォルトの http://localhost:9200 への接続を試みます。"
            )

        # get_es_client は設定オブジェクトを受け取るように変更
        es_client = get_es_client(config)
        view.display_info("Elasticsearchに接続中...")
        if not es_client.ping():
            raise ElasticsearchError(
                "Elasticsearch に接続できません。設定とサーバーの状態を確認してください。"
            )
        view.display_info("Elasticsearchに接続しました。")
        return es_client
    except Exception as e:
        # get_es_client 内のエラーや ping() のエラーを含む
        raise ElasticsearchError(
            f"Elasticsearchクライアントの初期化または接続確認中にエラーが発生しました: {e}"
        ) from e


# --- 依存関係コンテナ (オプション) ---
# より複雑な依存関係管理が必要な場合、DIコンテナライブラリ (例: dependency-injector) の導入も検討
class AppContainer:
    """依存関係を保持するコンテナ (シンプルな例)"""

    def __init__(self, config: AppConfig, view: QuestView):
        self.config = config
        self.view = view
        self._quest_repo = None
        self._es_client = None

    @property
    def quest_repository(self) -> QuestRepository:
        if self._quest_repo is None:
            self._quest_repo = initialize_database(self.config, self.view)
        return self._quest_repo

    @property
    def es_client(self) -> Elasticsearch:
        if self._es_client is None:
            self._es_client = initialize_elasticsearch(self.config, self.view)
        return self._es_client

    # 必要に応じて Service のインスタンスもここで生成・管理できる
    # def quest_service(self) -> QuestService: ...
