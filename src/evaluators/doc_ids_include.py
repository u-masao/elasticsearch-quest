# src/evaluators/doc_ids_include.py
from typing import Any, Dict, List, Set, Tuple

from .base import Evaluator


class DocIdsIncludeEvaluator(Evaluator):
    """特定のドキュメントIDが結果に含まれているかで評価するクラス（順序不問）。"""

    def __init__(self, expected_data: Any):
        if not isinstance(expected_data, list) or not all(
            isinstance(item, str) for item in expected_data
        ):
            # 不正なデータ型の場合はTypeErrorを送出
            raise TypeError(
                f"[System Error] 評価データ型エラー (doc_ids_include): "
                f"期待する型=List[str], 実際の型={type(expected_data).__name__}"
            )
        super().__init__(expected_data)

    def evaluate(self, es_response: Dict[str, Any]) -> Tuple[bool, str]:
        total_hits, actual_hits_list = self._get_hits_info(es_response)
        expected_ids: List[str] = self.expected_data  # 型チェック済み
        expected_ids_set: Set[str] = set(expected_ids)

        actual_ids: Set[str] = {hit["_id"] for hit in actual_hits_list}
        # 期待されるIDのうち、実際の結果に含まれていないものを抽出
        missing_ids: List[str] = sorted(list(expected_ids_set - actual_ids))

        is_correct = not missing_ids  # missing_ids が空なら正解
        expected_ids_str = ", ".join(expected_ids)  # メッセージ表示用に整形

        if is_correct:
            message = f"正解！必要なドキュメントID ({expected_ids_str}) がすべて含まれています。ヒット数: {total_hits}"
        else:
            missing_ids_str = ", ".join(missing_ids)
            message = f"不正解... 必要なドキュメントIDのうち {missing_ids_str} が見つかりません。ヒット数: {total_hits}"
        return is_correct, message
