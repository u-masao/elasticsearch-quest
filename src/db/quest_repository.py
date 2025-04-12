# src/db/quest_repository.py
import sqlite3
import os
from typing import List, Optional
from contextlib import contextmanager

# Questデータクラスをインポート (上記で定義)
from src.models.quest import Quest


class QuestRepository:
    """クエストテーブルを操作するためのリポジトリクラス"""

    def __init__(self, db_path: str):
        """
        リポジトリを初期化し、データベースパスを設定します。

        Args:
            db_path: SQLiteデータベースファイルのパス。':memory:'も可。
        """
        if not db_path:
            raise ValueError("Database path cannot be empty.")
        self.db_path = db_path
        # 接続はメソッドごとに行うか、必要に応じて永続的な接続を持つことも可能

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
                # テーブル存在確認 (より堅牢にするなら)
                # cursor = conn.cursor()
                # cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quests';")
                # if cursor.fetchone() is None:
                #     conn.executescript(schema_sql)
                # 初回実行前提なら以下でOK
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
                # executemany や個別のINSERT文実行の方がエラーハンドリングしやすい場合も
                conn.executescript(data_sql)
                conn.commit()
        except sqlite3.Error as e:
            print(f"Failed to load data from {data_file}: {e}")
            # データロード失敗時のロールバックなどを検討
            raise

    def _row_to_quest(self, row: sqlite3.Row) -> Optional[Quest]:
        """sqlite3.RowをQuestオブジェクトに変換"""
        if not row:
            return None
        return Quest(
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

    def get_quest_by_id(self, quest_id: int) -> Optional[Quest]:
        """
        指定されたIDのクエストを取得します。

        Args:
            quest_id: 取得するクエストのID。

        Returns:
            Questオブジェクト、または見つからない場合はNone。
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM quests WHERE quest_id = ?", (quest_id,))
                row = cursor.fetchone()
                return self._row_to_quest(row)
        except sqlite3.Error as e:
            print(f"Error fetching quest with id {quest_id}: {e}")
            return None  # エラー時はNoneを返す

    def get_all_quests(self, order_by_difficulty: bool = True) -> List[Quest]:
        """
        すべてのクエストを取得します。

        Args:
            order_by_difficulty: Trueの場合、難易度順(昇順)でソートします。

        Returns:
            Questオブジェクトのリスト。
        """
        query = "SELECT * FROM quests"
        if order_by_difficulty:
            query += " ORDER BY difficulty ASC, quest_id ASC"  # 難易度が同じ場合はID順

        quests = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                for row in rows:
                    quest = self._row_to_quest(row)
                    if quest:  # 変換に成功した場合のみ追加
                        quests.append(quest)
            return quests
        except sqlite3.Error as e:
            print(f"Error fetching all quests: {e}")
            return []  # エラー時は空リストを返す
