# src/core_logic.py
import json
from typing import Any, Dict, Optional, Tuple

from elasticsearch import Elasticsearch, TransportError

from src.db.quest_repository import QuestRepository  # QuestRepositoryを想定

# 必要なクラスや関数をインポート
from src.models.quest import Quest


def execute_query(
    es_client: Elasticsearch, index_name: str, user_query_str: str
) -> Dict[str, Any]:
    """
    ユーザーが入力したJSON形式のクエリ文字列をElasticsearchで実行し、
    結果(レスポンス全体)を返す。

    Args:
        es_client: Elasticsearchクライアントインスタンス。
        index_name: 検索対象のインデックス名。
        user_query_str: ユーザーが入力したJSON形式のクエリ文字列。

    Returns:
        Elasticsearchからのレスポンス (dict)。

    Raises:
        ValueError: クエリ文字列が不正なJSONの場合。
        TransportError: Elasticsearchへのクエリ実行時にエラーが発生した場合。
        Exception: その他の予期せぬエラー。
    """
    try:
        # ユーザー入力をJSONとしてパース
        # knn検索など、クエリがトップレベルのキーを持つ場合も考慮
        # 例えば {"query": {...}} や {"knn": {...}, "query": {...}} など
        query_body = json.loads(user_query_str)
        if not isinstance(query_body, dict):
            raise ValueError("Query must be a JSON object.")

        print(f"\nExecuting query on index '{index_name}':")
        print(json.dumps(query_body, indent=2, ensure_ascii=False))

        # Elasticsearchにクエリを実行
        response = es_client.search(index=index_name, body=query_body)
        return response

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in query: {e}")
    except TransportError as e:
        # Elasticsearch固有のエラー (クエリ構文エラーなどを含む可能性)
        print(f"Elasticsearch query error: {e.info}")  # エラー詳細を表示
        raise  # エラーを再送出
    except Exception as e:
        print(f"An unexpected error occurred during query execution: {e}")
        raise


def evaluate_result(quest: Quest, es_response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    クエストの評価基準に基づき、Elasticsearchの実行結果を評価する。

    Args:
        quest: 評価対象のQuestオブジェクト。
        es_response: Elasticsearchからのレスポンス。

    Returns:
        Tuple[bool, str]: (正解かどうか, 評価メッセージ)
    """

    try:
        eval_type = quest.evaluation_type
        expected_data = quest.evaluation_data  # パース済みの期待データ
    except ValueError as e:
        return False, f"Quest のパース失敗: {e}"

    try:
        hits_info = es_response.get("hits", {})
        total_hits = hits_info.get("total", {}).get("value", 0)
        actual_hits = hits_info.get("hits", [])

        if eval_type == "result_count":
            if not isinstance(expected_data, int):
                return (
                    False,
                    f"[System Error] 評価用の正解データが不正です:  result_count: {type(expected_data)}",
                )
            is_correct = total_hits == expected_data
            message = (
                f"正解！ヒット数: {total_hits}"
                if is_correct
                else f"不正解... ヒット数: {total_hits} (期待値: {expected_data})"
            )
            return is_correct, message

        elif eval_type == "doc_ids_include":
            if not isinstance(expected_data, list):
                return (
                    False,
                    f"[System Error] 評価用の正解データが不正です:  doc_ids_include: {type(expected_data)}",
                )
            actual_ids = {hit["_id"] for hit in actual_hits}
            missing_ids = [
                doc_id for doc_id in expected_data if doc_id not in actual_ids
            ]
            is_correct = not missing_ids
            if is_correct:
                message = f"正解！必要なドキュメントID ({', '.join(expected_data)}) がすべて含まれています。ヒット数: {total_hits}"
            else:
                message = f"不正解... 必要なドキュメントIDのうち {', '.join(missing_ids)} が見つかりません。ヒット数: {total_hits}"
            return is_correct, message

        elif eval_type == "doc_ids_in_order":
            if not isinstance(expected_data, list):
                return (
                    False,
                    f"[System Error] 評価用の正解データが不正です:  doc_ids_in_order: {type(expected_data)}",
                )
            # 上位N件のみ比較 (期待するIDリストの長さで比較)
            num_expected = len(expected_data)
            actual_ids_ordered = [hit["_id"] for hit in actual_hits[:num_expected]]
            is_correct = actual_ids_ordered == expected_data
            if is_correct:
                message = f"正解！上位{num_expected}件のドキュメントIDが期待通り ({', '.join(expected_data)}) です。"
            else:
                message = f"不正解... 上位{num_expected}件のドキュメントIDが異なります。\n期待値: {expected_data}\n実際の結果: {actual_ids_ordered}"
            return is_correct, message

        elif eval_type == "aggregation_result":
            # 集計結果の比較は複雑になる可能性がある
            # ここでは単純な例として、特定の集計名と値が一致するかを見る
            # quest.evaluation_data が {"agg_name": "...", "expected_value": ...} のような形式を想定
            if not isinstance(expected_data, dict):
                return (
                    False,
                    f"[System Error] 評価用の正解データが不正です:  aggregation_result: {type(expected_data)}",
                )

            aggregations = es_response.get("aggregations")
            if not aggregations:
                return False, "不正解... 集計結果が含まれていません。"

            # 期待する集計名と値を取得 (例)
            expected_agg_name = expected_data.get("agg_name")
            expected_value = expected_data.get(
                "expected_value"
            )  # 比較する値 (数値、文字列、dictなど)

            if not expected_agg_name:
                return (
                    False,
                    "[System Error] aggregation_resultに 'agg_name' が定義されていません。",
                )

            actual_agg = aggregations.get(expected_agg_name)
            if actual_agg is None:
                return (
                    False,
                    f"不正解... 集計結果に '{expected_agg_name}' が見つかりません。",
                )

            # TODO: 実際の値の比較ロジックを実装 (単純な値比較、構造比較など)
            # 例: 単純な値の場合
            actual_value = actual_agg.get("value")  # .value 形式の場合
            is_correct = actual_value == expected_value
            if is_correct:
                message = f"正解！集計 '{expected_agg_name}' の値が期待通り ({expected_value}) です。"
            else:
                message = f"不正解... 集計 '{expected_agg_name}' の値が異なります。\n期待値: {expected_value}\n実際の結果: {actual_value}"

            # より複雑な集計結果 (bucketsなど) の比較は別途実装が必要
            # is_correct = (actual_agg == expected_value) # 構造全体を比較する場合 (JSON文字列で格納など)

            return is_correct, message

        else:
            return False, f"[System Error] 未定義の評価タイプです: {eval_type}"

    except Exception as e:
        print(f"An error occurred during evaluation: {e}")
        return False, f"[System Error] 評価中にエラーが発生しました: {e}"


def get_feedback(quest: Quest, is_correct: bool, attempt_count: int) -> str:
    """
    評価結果や試行回数に基づき、ユーザーへのフィードバック（ヒントなど）を生成する。

    Args:
        quest: 対象のQuestオブジェクト。
        is_correct: 評価結果 (正解かどうか)。
        attempt_count: ユーザーの試行回数。

    Returns:
        フィードバックメッセージ文字列。
    """
    feedback = ""
    if not is_correct:
        feedback += "もう一度試してみましょう。\n"
        hints = quest.hints  # パース済みのヒントリスト
        if hints:
            # 試行回数に応じてヒントを出す (例: 1回目はヒント1、2回目はヒント2...)
            hint_index = attempt_count - 1  # 0-based index
            if 0 <= hint_index < len(hints):
                feedback += f"ヒント {attempt_count}: {hints[hint_index]}"
            elif hint_index >= len(hints):
                feedback += f"ヒント {len(hints)}: {hints[-1]} (これが最後のヒントです)"
            else:  # attempt_countが0以下の場合など(通常はないはず)
                feedback += f"ヒント 1: {hints[0]}"  # 最初のヒントを出す
        else:
            feedback += "この問題には利用可能なヒントがありません。"

    # 正解時のメッセージは evaluate_result 側で生成済みなので、ここでは追加しない
    # 必要であれば、正解時にも追加のメッセージ（例：「素晴らしい！」など）を生成

    return feedback


# --- 解答例関連 ---
# QuestRepositoryに解答例取得メソッドが追加されたと仮定
def get_example_solution(quest_repo: QuestRepository, quest_id: int) -> Optional[str]:
    """
    指定されたクエストIDの解答例を取得する (DBに保存されている場合)
    """
    solution = quest_repo.get_solution_by_quest_id(quest_id)  # 仮のメソッド名
    if solution:
        try:
            # 整形して返す
            parsed_solution = json.loads(solution)
            return json.dumps(parsed_solution, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return solution  # パースできない場合はそのまま返す
    return None


# LLMを使って解答例を「作る」機能は、別途LLM連携部分で実装が必要
def generate_example_solution_with_llm(quest: Quest) -> str:
    """(将来実装) LLMを使ってクエストの解答例を生成する"""
    # LLM API呼び出しロジック
    pass
