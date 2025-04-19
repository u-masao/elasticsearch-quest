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
        with self.json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        quests_data = data.get('quests', [])
        return [Quest(**quest) for quest in quests_data]
