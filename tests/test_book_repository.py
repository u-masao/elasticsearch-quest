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


def test_empty_quests(tmp_path: Path):
    # テスト用のJSONデータを作成 (questsキーが空)
    test_data = {"quests": []}
    file_path = tmp_path / "book.json"
    file_path.write_text(json.dumps(test_data), encoding="utf-8")
    repo = BookRepository(file_path)
    quests = repo.load_quests()
    assert quests == []


def test_invalid_evaluation_data(tmp_path: Path):
    # evaluation_data_raw が int にパースできない場合、ValueError が発生することを確認
    test_data = {
        "quests": [
            {
                "quest_id": 2,
                "title": "Invalid Eval Data Quest",
                "description": "A quest with invalid evaluation data",
                "difficulty": 1,
                "query_type_hint": "match",
                "evaluation_type": "result_count",
                "evaluation_data_raw": "invalid",
                "hints_raw": '["Hint"]',
                "created_at": "2025-04-19T00:00:00",
                "updated_at": "2025-04-19T00:00:00",
            }
        ]
    }
    file_path = tmp_path / "book_invalid_eval.json"
    file_path.write_text(json.dumps(test_data), encoding="utf-8")
    repo = BookRepository(file_path)
    with pytest.raises(ValueError):
        _ = repo.load_quests()


def test_invalid_hints(tmp_path: Path):
    # hints_raw が不正なJSONの場合、ValueError が発生することを確認
    test_data = {
        "quests": [
            {
                "quest_id": 3,
                "title": "Invalid Hints Quest",
                "description": "A quest with invalid hints",
                "difficulty": 1,
                "query_type_hint": "match",
                "evaluation_type": "result_count",
                "evaluation_data_raw": "5",
                "hints_raw": "invalid_json",
                "created_at": "2025-04-19T00:00:00",
                "updated_at": "2025-04-19T00:00:00",
            }
        ]
    }
    file_path = tmp_path / "book_invalid_hints.json"
    file_path.write_text(json.dumps(test_data), encoding="utf-8")
    repo = BookRepository(file_path)
    with pytest.raises(ValueError):
        _ = repo.load_quests()


def test_multiple_quests(tmp_path: Path):
    # 複数のクエストが含まれる場合のテスト
    test_data = {
        "quests": [
            {
                "quest_id": 1,
                "title": "First Quest",
                "description": "First test quest",
                "difficulty": 2,
                "query_type_hint": "match",
                "evaluation_type": "result_count",
                "evaluation_data_raw": "10",
                "hints_raw": '["First Hint"]',
                "created_at": "2025-04-19T00:00:00",
                "updated_at": "2025-04-19T00:00:00",
            },
            {
                "quest_id": 2,
                "title": "Second Quest",
                "description": "Second test quest",
                "difficulty": 3,
                "query_type_hint": "term",
                "evaluation_type": "doc_ids_include",
                "evaluation_data_raw": "[1, 2, 3]",
                "hints_raw": '["Second Hint"]',
                "created_at": "2025-04-19T00:00:00",
                "updated_at": "2025-04-19T00:00:00",
            },
        ]
    }
    file_path = tmp_path / "book_multiple.json"
    file_path.write_text(json.dumps(test_data), encoding="utf-8")
    repo = BookRepository(file_path)
    quests = repo.load_quests()
    assert len(quests) == 2
    first, second = quests
    assert first.quest_id == 1
    assert first.title == "First Quest"
    assert first.evaluation_data == 10
    assert first.hints == ["First Hint"]
    assert second.quest_id == 2
    assert second.title == "Second Quest"
    assert second.evaluation_data == [1, 2, 3]
    assert second.hints == ["Second Hint"]
