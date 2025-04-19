# src/db/quest_repository.py
import os
from typing import List, Optional

from src.models.quest import Quest


class QuestRepository:
    """クエストテーブルを操作するためのリポジトリクラス"""

    def __init__(self):
        """
        リポジトリを初期化し、クエストのJSONファイルを設定します。
        デフォルトで fixtures/tests/quests.json を使用します。
        """
        self.quest_file = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "tests", "quests.json"
        )

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

    def _read_quests(self) -> List[dict]:
        import json

        quest_file = self.quest_file
        if not os.path.exists(quest_file):
            raise FileNotFoundError(f"Quest file not found: {quest_file}")
        with open(quest_file, "r", encoding="utf-8") as f:
            quests_json = json.load(f)
        print(f"Number of quests loaded: {len(quests_json)}")
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
