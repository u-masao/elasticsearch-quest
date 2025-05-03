# tests/conftest.py
import sys
from pathlib import Path

import pytest

# QuestRepositoryをインポート
from src.db.quest_repository import QuestRepository

# プロジェクトルートをパスに追加（srcをインポートするため）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# フィクスチャファイルのパスを定義
FIXTURES_DIR = project_root / "fixtures"
SCHEMA_FILE = FIXTURES_DIR / "create_quests_table.sql"
DATA_FILE = FIXTURES_DIR / "insert_quests.sql"
BOOK_FILE = FIXTURES_DIR / "books" / "default.json"


@pytest.fixture(scope="function")  # 各テスト関数ごとにDBを初期化
def quest_repository() -> QuestRepository:
    """
    テスト用のファイルベース一時QuestRepositoryインスタンスを提供するFixture。
    スキーマとサンプルデータをロードする。
    テスト終了後にDBファイルを削除する。
    """
    repo = QuestRepository(BOOK_FILE)
    yield repo
