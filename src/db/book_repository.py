from pathlib import Path
import json
from src.models.quest import Quest


class BookRepository:
    """
    book.json を読み込んで管理するリポジトリクラス。
    'quests' キーの各要素を Quest オブジェクトのリストに変換します。
    """

    def __init__(self, json_path: Path):
        self.json_path = json_path

    def load_quests(self) -> list[Quest]:
        """
        book.json ファイルから 'quests' を読み込み、
        Quest オブジェクトのリストを返します。
        """
        with self.json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        quests_data = data.get("quests", [])
        quests = []
        for quest_dict in quests_data:
            if "evaluation_data" in quest_dict:
                quest_dict["evaluation_data_raw"] = quest_dict.pop("evaluation_data")
            if "hints" in quest_dict:
                quest_dict["hints_raw"] = quest_dict.pop("hints")
            quest = Quest(**quest_dict)
            # パース済みプロパティの評価を強制して、パースエラーを発生させる
            _ = quest.evaluation_data
            _ = quest.hints
            quests.append(quest)
        return quests
