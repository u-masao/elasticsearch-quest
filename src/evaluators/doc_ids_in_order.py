# src/evaluators/doc_ids_in_order.py
from typing import Any, Dict, List, Tuple

from .base import Evaluator


class DocIdsInOrderEvaluator(Evaluator):
    """検索結果のドキュメントIDが期待される順序と一致するかで評価するクラス。"""

    def __init__(self, expected_data: Any):
        if not isinstance(expected_data, list) or not all(
            isinstance(item, str) for item in expected_data
        ):
            # 不正なデータ型の場合はTypeErrorを送出
            raise TypeError(
                f"[System Error] 評価データ型エラー (doc_ids_in_order): "
                f"期待する型=List[str], 実際の型={type(expected_data).__name__}"
            )
        super().__init__(expected_data)

    def evaluate(self, es_response: Dict[str, Any]) -> Tuple[bool, str]:
        _, actual_hits_list = self._get_hits_info(es_response)
        expected_ids_ordered: List[str] = self.expected_data  # 型チェック済み

        num_expected = len(expected_ids_ordered)
        # 実際の結果から期待される件数分のIDを順序通りに取得
        actual_ids_ordered: List[str] = [
            hit["_id"] for hit in actual_hits_list[:num_expected]
        ]

        is_correct = actual_ids_ordered == expected_ids_ordered
        expected_ids_str = ", ".join(expected_ids_ordered)  # メッセージ表示用

        if is_correct:
            message = f"正解！上位{num_expected}件のドキュメントIDが期待通り ({expected_ids_str}) です。"
        else:
            actual_ids_str = ", ".join(actual_ids_ordered)
            message = (
                f"不正解... 上位{num_expected}件のドキュメントIDが異なります。\n"
                f"期待値: {expected_ids_ordered}\n"
                f"実際の結果: {actual_ids_str}"
            )
        return is_correct, message
