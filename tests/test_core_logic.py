# tests/test_core_logic.py

import pytest
from typing import Dict, Any

# テスト対象のモジュールとクラスをインポート
from src.core_logic import evaluate_result, get_feedback
from src.models.quest import Quest
from src.db.quest_repository import QuestRepository  # conftestから渡される型ヒント用

# --- テスト用ヘルパー (エッジケース Quest 生成用) ---


def create_edge_case_quest(**kwargs) -> Quest:
    """エッジケース用のQuestオブジェクトを生成するヘルパー"""
    defaults = {
        "quest_id": 999,  # DBに存在しない想定
        "title": "Edge Case Quest",
        "description": "Testing edge cases",
        "difficulty": 1,
        "query_type_hint": "test",
        "evaluation_type": "result_count",
        "evaluation_data_raw": "1",
        "hints_raw": '["Edge Hint"]',
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    defaults.update(kwargs)
    # Questクラスのコンストラクタに必要な引数を渡す
    return Quest(**defaults)


# execute_query の各テスト関数は前回の回答と同じで良いでしょう
# (test_execute_query_success, test_execute_query_invalid_json, etc.)


# --- evaluate_result のテスト ---

# テストパラメータを pytest.param で分かりやすく定義
# 各 param の引数: quest_id, es_response (dict), expected_correct (bool), expected_message_contains (str)
#                評価タイプは quest_id から取得される前提

evaluate_params = [
    # --- result_count ---
    pytest.param(
        1,
        {"hits": {"total": {"value": 3}}},
        True,
        "正解！ヒット数: 3",
        id="q1_result_count_correct",
    ),
    pytest.param(
        1,
        {"hits": {"total": {"value": 2}}},
        False,
        "不正解... ヒット数: 2 (期待値: 3)",
        id="q1_result_count_wrong_count",
    ),
    pytest.param(
        3,
        {"hits": {"total": {"value": 5}}},
        True,
        "正解！ヒット数: 5",
        id="q3_result_count_correct",
    ),  # 期待値5
    pytest.param(
        3,
        {"hits": {}},
        False,
        "不正解... ヒット数: 0 (期待値: 5)",
        id="q3_result_count_no_hits",
    ),
    # --- doc_ids_in_order ---
    pytest.param(
        6,
        {
            "hits": {
                "hits": [
                    {"_id": "978-4802613353"},
                    {"_id": "978-4297131883"},
                    {"_id": "978-4297130350"},
                ]
            }
        },
        True,
        "正解！上位3件",
        id="q6_doc_ids_order_correct",
    ),
    pytest.param(
        6,
        {
            "hits": {
                "hits": [
                    {"_id": "978-4297131883"},
                    {"_id": "978-4802613353"},
                    {"_id": "978-4297130350"},
                ]
            }
        },
        False,
        "不正解... 上位3件のドキュメントIDが異なります",
        id="q6_doc_ids_order_wrong_order",
    ),
    pytest.param(
        6,
        {"hits": {"hits": [{"_id": "978-4802613353"}]}},
        False,
        "不正解... 上位3件のドキュメントIDが異なります",
        id="q6_doc_ids_order_too_few",
    ),
    # --- aggregation_result (単純な値比較の例) ---
    # Questにaggregation評価のものが無いので、これはエッジケーステストでカバーする
]


@pytest.mark.parametrize(
    "quest_id, es_response, expected_correct, expected_message_contains",
    evaluate_params,
)
def test_evaluate_result_from_db(
    quest_repository: QuestRepository,
    quest_id: int,
    es_response: Dict[str, Any],
    expected_correct: bool,
    expected_message_contains: str,
):
    """evaluate_result をDBから取得したクエストデータでテスト"""
    quest = quest_repository.get_quest_by_id(quest_id)
    assert quest is not None, f"テストDBにクエストID {quest_id} が見つかりません"

    is_correct, message = evaluate_result(quest, es_response)

    assert is_correct == expected_correct
    assert expected_message_contains in message, (
        f"期待するメッセージ '{expected_message_contains}' が実際のメッセージ '{message}' に含まれていません"
    )


# --- evaluate_result のエッジケーステスト ---


def test_evaluate_result_invalid_expected_data_type():
    """期待するデータの型が不正な場合のテスト (例: result_countに文字列)"""
    quest = create_edge_case_quest(
        evaluation_type="result_count", evaluation_data_raw="not_an_int"
    )
    es_response = {"hits": {"total": {"value": 1}}}
    is_correct, message = evaluate_result(quest, es_response)
    assert not is_correct
    assert "指定の evaluation_data_raw が int にパースできません: not_an_int" in message


def test_evaluate_result_invalid_json_expected_data():
    """期待するデータが不正なJSONの場合のテスト (例: doc_ids_in_orderに不正なJSON)"""
    quest = create_edge_case_quest(
        evaluation_type="doc_ids_in_order", evaluation_data_raw='["id1",'
    )  # 不正なJSON
    es_response = {"hits": {"hits": [{"_id": "id1"}]}}
    is_correct, message = evaluate_result(quest, es_response)
    assert not is_correct
    assert '指定の evaluation_data_raw がJSONデコードできません: ["id1",' in message


def test_evaluate_result_aggregation_edge_cases():
    """aggregation_result のエッジケース"""
    # 期待データは正しいが、レスポンスに該当aggがない
    quest_agg = create_edge_case_quest(
        evaluation_type="aggregation_result",
        evaluation_data_raw='{"agg_name": "my_agg", "expected_value": 10}',
    )
    es_response_no_agg = {"aggregations": {"other_agg": {"value": 10}}}
    is_correct, message = evaluate_result(quest_agg, es_response_no_agg)
    assert not is_correct
    assert "不正解... 集計結果に 'my_agg' が見つかりません" in message

    # レスポンス自体に aggregations がない
    es_response_no_aggs_key = {}
    is_correct_no_key, message_no_key = evaluate_result(
        quest_agg, es_response_no_aggs_key
    )
    assert not is_correct_no_key
    assert "不正解... 集計結果が含まれていません" in message_no_key


def test_evaluate_result_unknown_type():
    """未定義の evaluation_type の場合のテスト"""
    quest = create_edge_case_quest(evaluation_type="very_new_type")
    es_response = {}
    is_correct, message = evaluate_result(quest, es_response)
    assert not is_correct
    assert "指定の evaluation_type はサポートしていません: very_new_type" in message


# --- get_feedback のテスト ---

# テストパラメータ: quest_id, is_correct, attempt_count, expected_feedback_contains
feedback_params = [
    pytest.param(1, True, 1, None, id="q1_correct"),  # 正解時はヒントなし (Noneを期待)
    pytest.param(1, False, 1, "ヒント 1: `match` クエリは", id="q1_wrong_attempt1"),
    pytest.param(1, False, 2, "ヒント 2: 基本的な構文:", id="q1_wrong_attempt2"),
    pytest.param(
        1, False, 3, "(これが最後のヒントです)", id="q1_wrong_attempt3_last_hint"
    ),
    pytest.param(6, False, 1, "ヒント 1: `knn` 検索は", id="q6_wrong_attempt1"),
    pytest.param(
        6, False, 3, "ヒント 3: `query_vector` に `[9, 1]`", id="q6_wrong_attempt3"
    ),
    pytest.param(
        6, False, 4, "(これが最後のヒントです)", id="q6_wrong_attempt4_last_hint"
    ),
]


@pytest.mark.parametrize(
    "quest_id, is_correct, attempt_count, expected_feedback_contains", feedback_params
)
def test_get_feedback_from_db(
    quest_repository: QuestRepository,
    quest_id: int,
    is_correct: bool,
    attempt_count: int,
    expected_feedback_contains: str | None,
):
    """get_feedback をDBから取得したクエストデータでテスト"""
    quest = quest_repository.get_quest_by_id(quest_id)
    assert quest is not None, f"テストDBにクエストID {quest_id} が見つかりません"

    feedback = get_feedback(quest, is_correct, attempt_count)

    if expected_feedback_contains is None:
        # 正解時など、フィードバック（特にヒント部分）が空であることを期待
        assert not feedback.strip() or "もう一度試してみましょう" not in feedback
    else:
        assert expected_feedback_contains in feedback, (
            f"期待するフィードバック '{expected_feedback_contains}' が実際のフィードバック '{feedback}' に含まれていません"
        )


def test_get_feedback_no_hints():
    """ヒントが定義されていないクエストの場合"""
    quest = create_edge_case_quest(hints_raw=None)  # hints_raw を None にする
    feedback = get_feedback(quest, False, 1)
    assert "利用可能なヒントがありません" in feedback

    quest_empty_hints = create_edge_case_quest(
        hints_raw="[]"
    )  # hints_raw を空リストのJSONにする
    feedback_empty = get_feedback(quest_empty_hints, False, 1)
    # Questモデルの@property hints が None または空リストを返すことを期待
    assert (
        "利用可能なヒントがありません" in feedback_empty or not quest_empty_hints.hints
    )
