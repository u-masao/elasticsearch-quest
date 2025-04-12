# tests/conftest.py
import pytest
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# プロジェクトルートをパスに追加（srcをインポートするため）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# QuestRepositoryをインポート
from src.db.quest_repository import QuestRepository

# フィクスチャファイルのパスを定義
FIXTURES_DIR = project_root / "fixtures"
SCHEMA_FILE = FIXTURES_DIR / "create_quests_table.sql"
DATA_FILE = FIXTURES_DIR / "insert_quests.sql"


@pytest.fixture(scope="function")  # 各テスト関数ごとにDBを初期化
def quest_repository() -> QuestRepository:
    """
    テスト用のファイルベース一時QuestRepositoryインスタンスを提供するFixture。
    スキーマとサンプルデータをロードする。
    テスト終了後にDBファイルを削除する。
    """
    # 一時ファイルを作成してそのパスを取得
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp_db_file:
        db_path = tmp_db_file.name
        print(f"Using temporary database: {db_path}")  # デバッグ用

    # 一時ファイルパスを使ってリポジトリを初期化
    repo = QuestRepository(db_path)

    # スキーマの存在確認
    if not SCHEMA_FILE.exists():
        os.unlink(db_path)  # 即座に一時ファイルを削除
        raise FileNotFoundError(f"Test schema file not found: {SCHEMA_FILE}")
    if not DATA_FILE.exists():
        os.unlink(db_path)  # 即座に一時ファイルを削除
        raise FileNotFoundError(f"Test data file not found: {DATA_FILE}")

    # スキーマとデータを初期化
    try:
        # initialize_schemaとload_dataは内部で接続を開いて閉じるが、
        # ファイルベースなのでテーブルとデータは永続化される
        repo.initialize_schema(str(SCHEMA_FILE))
        print(f"Schema initialized in {db_path}")  # デバッグ用
        repo.load_data(str(DATA_FILE))
        print(f"Data loaded into {db_path}")  # デバッグ用

        # データがロードされたか簡単な確認 (任意)
        # _get_connectionがpublicでない場合は直接接続する
        conn_check = None
        try:
            conn_check = sqlite3.connect(db_path)
            cursor = conn_check.cursor()
            cursor.execute("SELECT COUNT(*) FROM quests")
            count = cursor.fetchone()[0]
            print(f"Number of quests loaded: {count}")  # デバッグ用
            if count != 6:  # 期待されるクエスト数を確認
                raise Exception(
                    f"Data loading failed or incomplete ({count} quests found, expected 6)."
                )
        finally:
            if conn_check:
                conn_check.close()

    except Exception as e:
        # 初期化失敗時もファイルを削除
        try:
            os.unlink(db_path)
        except OSError:
            pass  # ファイルが存在しない場合など
        pytest.fail(f"Failed to initialize test database ({db_path}): {e}")

    # 初期化済みリポジトリをテスト関数に渡す
    yield repo

    # --- ここから後処理 ---
    # テスト関数実行後、一時DBファイルを削除する
    try:
        print(f"Cleaning up temporary database: {db_path}")  # デバッグ用
        os.unlink(db_path)
    except OSError as e:
        print(f"Error removing temporary database file {db_path}: {e}")
