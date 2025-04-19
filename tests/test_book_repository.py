import json
from pathlib import Path
import pytest
from src.db.book_repository import BookRepository


def test_load_quests(tmp_path: Path):
    # テスト用のJSONデータを作成
    test_data = {
        "quests": [
            {
                "quest_id": 1,
                "title": "Test Quest",
                "description": "A test quest",
                "difficulty": 1,
                "query_type_hint": "match",
                "evaluation_type": "result_count",
                "evaluation_data_raw": "3",
                "hints_raw": '["Hint 1", "Hint 2"]',
                "created_at": "2025-04-19T00:00:00",
                "updated_at": "2025-04-19T00:00:00",
            }
        ]
    }
    # tmp_path上に一時的なJSONファイルを作成
    file_path = tmp_path / "book.json"
    file_path.write_text(json.dumps(test_data), encoding="utf-8")

    # BookRepositoryを使用してquestsを読み込む
    repo = BookRepository(file_path)
    quests = repo.load_quests()

    assert len(quests) == 1
    quest = quests[0]
    assert quest.quest_id == 1
    assert quest.title == "Test Quest"
    assert quest.evaluation_data == 3
    assert quest.hints == ["Hint 1", "Hint 2"]
