# src/config.py
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, ConfigDict, Field, FilePath, field_validator
from pydantic_settings import BaseSettings

# .env ファイルをロード (プロジェクトルートにある想定)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# --- 定数 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_FILE_PATH = DEFAULT_DATA_DIR / "quests.db"
DEFAULT_FIXTURES_DIR = PROJECT_ROOT / "fixtures"
DEFAULT_INDEX_NAME = "sample_books"
DEFAULT_BOOK_FILE = DEFAULT_FIXTURES_DIR / "default_book.json"


# --- 設定クラス ---
class AppConfig(BaseSettings):
    """アプリケーション設定"""

    project_root: Path = Field(default=PROJECT_ROOT)
    db_path: Path = Field(default=DEFAULT_DB_FILE_PATH)
    book_path: Path = Field(default=DEFAULT_BOOK_FILE)
    index_name: str = Field(
        default=DEFAULT_INDEX_NAME, alias="ES_INDEX_NAME"
    )  # 環境変数名を指定

    # Elasticsearch接続情報
    elasticsearch_url: AnyHttpUrl | None = Field(
        default=None, alias="ELASTICSEARCH_URL"
    )
    elastic_cloud_id: str | None = Field(default=None, alias="ELASTIC_CLOUD_ID")
    elasticsearch_username: str | None = Field(
        default=None, alias="ELASTICSEARCH_USERNAME"
    )
    elasticsearch_password: str | None = Field(
        default=None, alias="ELASTICSEARCH_PASSWORD", repr=False
    )  # repr=Falseでログ等への出力を抑制
    elasticsearch_ca_cert: FilePath | None = Field(
        default=None, alias="ELASTICSEARCH_CA_CERT"
    )

    # MCP Server 設定
    mcp_server_command: str = Field(default="uv")
    # MCP Server のディレクトリはプロジェクトルートからの相対パスとする
    mcp_server_directory_relative: Path = Field(
        default=Path("mcp/elasticsearch-mcp-server")
    )
    mcp_server_module: str = Field(default="elasticsearch-mcp-server")

    # --- 計算済みプロパティ ---
    @property
    def mcp_server_directory(self) -> Path:
        # 絶対パスを返す
        return self.project_root / self.mcp_server_directory_relative

    # --- バリデーション ---
    @field_validator("db_path")
    @classmethod
    def db_path_must_have_parent(cls, v: Path):
        # 親ディレクトリが存在することを保証（なければ作成を試みる）
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def load_config(
    db_path_override: Path | None = None,
    index_name_override: str | None = None,
    book_path_override: Path | None = None,
) -> AppConfig:
    """
    設定をロードし、CLI引数で指定された値で上書きする。

    Args:
        db_path_override: DBファイルパス (CLI引数).
        index_name_override: Index名 (CLI引数).
        book_path_override: Book ファイルパス (CLI引数).

    Returns:
        ロードされたAppConfigオブジェクト.

    Raises:
        pydantic.ValidationError: 設定値のバリデーションに失敗した場合.
    """
    # pydantic-settings は自動で環境変数を読み込む
    # CLI引数による上書きを考慮
    override_values = {}
    if db_path_override:
        override_values["db_path"] = db_path_override
    if index_name_override:
        override_values["index_name"] = index_name_override
    if book_path_override:
        override_values["book_path"] = book_path_override

    # BaseSettingsを初期化し、上書き値を渡す
    # **override_values で辞書を展開してキーワード引数として渡す
    return AppConfig(**override_values)
