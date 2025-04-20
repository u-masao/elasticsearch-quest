# src/db/quest_repository.py
from typing import List, Optional

from src.models.quest import Quest


class QuestRepository:
    """クエストテーブルを操作するためのリポジトリクラス"""

    def __init__(self):
        """
        リポジトリを初期化し、BookRepository を利用してクエストのリストを内部
        に保持します。
        """
        from pathlib import Path

        from src.db.book_repository import BookRepository

        book_json_path = (
            Path(__file__)
            .parent.joinpath("..", "..", "fixtures", "tests", "book.json")
            .resolve()
        )
        self.book_repo = BookRepository(book_json_path)
        self.quests = self.book_repo.load_quests()

    def _row_to_quest(self, row: dict) -> Optional[Quest]:
        """辞書をQuestオブジェクトに変換"""
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

    def get_quest_by_id(self, quest_id) -> Optional[Quest]:
        """
        指定されたIDのクエストを内部のリストから取得します。

        Args:
            quest_id: 取得するクエストのID (数値または文字列)。

        Returns:
            Questオブジェクト、または見つからない場合はNone。
        """
        for quest in self.quests:
            if str(quest.quest_id) == str(quest_id):
                return quest
        return None

    def get_all_quests(self, order_by_difficulty: bool = True) -> List[Quest]:
        """
        すべてのクエストを取得します。

        Args:
            order_by_difficulty: Trueの場合、難易度順(昇順)でソートします。

        Returns:
            Questオブジェクトのリスト。
        """
        quests = self.quests.copy()
        if order_by_difficulty:
            quests.sort(key=lambda q: (q.difficulty, q.quest_id))
        return quests
