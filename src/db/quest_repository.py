# src/db/quest_repository.py
import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

from src.models.quest import Quest


class QuestRepository:
    """クエストテーブルを操作するためのリポジトリクラス"""

    def __init__(self, db_path: str):
        """
        リポジトリを初期化し、データベースパスを設定します。

        Args:
            db_path: SQLiteデータベースファイルのパス。
        """
        if not db_path:
            raise ValueError("db_path が空です。ファイル名を指定してください。")
        self.db_path = db_path

    @contextmanager
    def _get_connection(self):
        """データベース接続を管理するコンテキストマネージャ"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # カラム名でアクセスできるようにする
            yield conn
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            # エラーハンドリング: 必要に応じてログ出力や再試行など
            raise  # エラーを再送出
        finally:
            if conn:
                conn.close()

    def initialize_schema(self, schema_file: str):
        """
        指定されたSQLファイルを実行してデータベーススキーマを初期化します。
        テーブルが存在する場合は実行しないなどの考慮も可能。
        """
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        try:
            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
        except sqlite3.Error as e:
            print(f"Failed to initialize schema from {schema_file}: {e}")
            raise

    def load_data(self, data_file: str):
        """
        指定されたSQLファイルを実行してデータをロードします。
        データの重複挿入を防ぐ考慮が必要な場合がある。
        """
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Data file not found: {data_file}")
        with open(data_file, "r", encoding="utf-8") as f:
            data_sql = f.read()
        try:
            with self._get_connection() as conn:
                conn.executescript(data_sql)
                conn.commit()
        except sqlite3.Error as e:
            print(f"Failed to load data from {data_file}: {e}")
            raise

    def _row_to_quest(self, row: sqlite3.Row) -> Optional[Quest]:
        """sqlite3.RowをQuestオブジェクトに変換"""
        if not row:
            return None
        quest = Quest(
            quest_id=row["quest_id"],
            title=row["title"],
            description=row["description"],
            difficulty=row["difficulty"],
            query_type_hint=row["query_type_hint"],
            evaluation_type=row["evaluation_type"],
            evaluation_data_raw=row["evaluation_data"],  # カラム名注意
            hints_raw=row["hints"],  # カラム名注意
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        _ = quest.as_dict()  # 強制的にパースを走らせる。
        return quest

    def _read_quests(self) -> List[dict]:
        import json

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Quest file not found: {self.db_path}")
        with open(self.db_path, "r", encoding="utf-8") as f:
            quests_json = json.load(f)
        return quests_json

    async def get_quest_by_id_async(self, quest_id: int) -> Optional[Quest]:
        return self.get_quest_by_id(quest_id)

    def get_quest_by_id(self, quest_id: int) -> Optional[Quest]:
        """
        指定されたIDのクエストを取得します。

        Args:
            quest_id: 取得するクエストのID。

        Returns:
            Questオブジェクト、または見つからない場合はNone。
        """
        try:
            quests = self._read_quests()
            for row in quests:
                if row["quest_id"] == quest_id:
                    return self._row_to_quest(row)
            return None
        except Exception as e:
            print(f"Error fetching quest with id {quest_id}: {e}")
            return None

    def get_all_quests(self, order_by_difficulty: bool = True) -> List[Quest]:
        """
        すべてのクエストを取得します。

        Args:
            order_by_difficulty: Trueの場合、難易度順(昇順)でソートします。

        Returns:
            Questオブジェクトのリスト。
        """
        try:
            quests_data = self._read_quests()
            quests = [
                self._row_to_quest(row)
                for row in quests_data
                if self._row_to_quest(row) is not None
            ]
            if order_by_difficulty:
                quests.sort(key=lambda q: (q.difficulty, q.quest_id))
            return quests
        except Exception as e:
            print(f"Error fetching all quests: {e}")
            return []
