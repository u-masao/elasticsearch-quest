# tests/test_quest_repository.py
import sys
from pathlib import Path

# モデルとリポジトリをインポート
from src.db.quest_repository import QuestRepository
from src.models.quest import Quest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# conftest.py から fixture を利用

# --- テストケース ---


def test_get_quest_by_id_exists(quest_repository: QuestRepository):
    """存在するクエストIDで取得できるかテスト"""
    quest = quest_repository.get_quest_by_id(1)
    assert quest is not None
    assert isinstance(quest, Quest)
    assert quest.quest_id == 1
    assert quest.title == "書籍名検索 (Match)"
    assert quest.difficulty == 1
    assert quest.evaluation_type == "result_count"
    # evaluation_data はプロパティ経由でパース済みデータを取得
    assert quest.evaluation_data == 3
    # hints もプロパティ経由でパース
    assert quest.hints == [
        "`match` クエリは、指定されたテキストを解析し、"
        "一致するドキュメントを検索します。",
        '基本的な構文: `query: { match: { field_name: "search_term" } }`',
    ]


def test_get_quest_by_id_not_exists(quest_repository: QuestRepository):
    """存在しないクエストIDでNoneが返るかテスト"""
    quest = quest_repository.get_quest_by_id(999)
    assert quest is None


def test_get_all_quests_sorted(quest_repository: QuestRepository):
    """全てのクエストが難易度順で取得できるかテスト"""
    quests = quest_repository.get_all_quests(order_by_difficulty=True)
    assert len(quests) == 20  # 投入したクエスト数

    # 難易度順になっているか確認
    difficulties = [q.difficulty for q in quests]
    assert difficulties == sorted(difficulties)

    # 最初のクエストと最後のクエストの簡単なチェック
    print(quests[-1])
    assert quests[0].difficulty == 1
    assert quests[0].title == "書籍名検索 (Match)"  # 難易度1が複数ある場合ID順
    assert quests[-1].difficulty == 5
    assert quests[-1].title == (
        "テキスト検索 + ベクトル類似検索 + フィルタ (Query + kNN)"
    )  # 難易度5が複数ある場合ID順


def test_get_all_quests_not_sorted(quest_repository: QuestRepository):
    """全てのクエストがソートなしで取得できるかテスト"""
    quests = quest_repository.get_all_quests(order_by_difficulty=False)
    assert len(quests) == 20
    # 順序は保証されないが、件数は正しいはず


def test_quest_data_details(quest_repository: QuestRepository):
    """特定のクエストのデータ詳細をテスト (特にJSONパース)"""
    # クエスト4: Bool検索
    quest4 = quest_repository.get_quest_by_id(4)
    assert quest4 is not None
    assert quest4.title == "複数条件検索 (Bool - Filter)"
    assert quest4.difficulty == 2
    assert quest4.query_type_hint == "bool, term, range"
    assert quest4.evaluation_type == "result_count"
    assert quest4.evaluation_data == 3  # 修正後の値
    assert isinstance(quest4.hints, list)
    assert len(quest4.hints) == 3

    # クエスト17: kNN検索
    quest17 = quest_repository.get_quest_by_id(17)
    assert quest17 is not None
    assert quest17.title == "ベクトル類似検索 (kNN)"
    assert quest17.difficulty == 3
    assert quest17.query_type_hint == "knn"
    assert quest17.evaluation_type == "doc_ids_in_order"
    # evaluation_data はJSONリストとしてパースされるはず
    assert isinstance(quest17.evaluation_data, list)
    assert quest17.evaluation_data == ["10", "11", "18"]
    assert isinstance(quest17.hints, list)
    assert len(quest17.hints) == 3


def test_evaluation_data_parsing(quest_repository: QuestRepository):
    """evaluation_dataがevaluation_typeに応じて正しくパースされるか"""
    q1 = quest_repository.get_quest_by_id(1)  # result_count -> int
    assert isinstance(q1.evaluation_data, int)
    assert q1.evaluation_data == 3

    q17 = quest_repository.get_quest_by_id(17)  # doc_ids_in_order -> list
    assert isinstance(q17.evaluation_data, list)
    assert q17.evaluation_data == ["10", "11", "18"]

    # evaluation_dataが不正なJSONの場合のテストも追加可能
    # (今回はサンプルデータが正しい前提)


def test_hints_parsing(quest_repository: QuestRepository):
    """hintsがJSONリストとして正しくパースされるか"""
    q1 = quest_repository.get_quest_by_id(1)
    assert isinstance(q1.hints, list)
    assert len(q1.hints) == 2
    assert q1.hints[0].startswith("`match` クエリは")

    # ヒントがないクエスト (もしあれば) や、不正なJSONの場合のテストも考慮
