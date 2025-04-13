# src/evaluators/result_count.py
from typing import Any, Dict, Tuple

from .base import Evaluator


class ResultCountEvaluator(Evaluator):
    """検索結果のヒット数で評価するクラス。"""

    def __init__(self, expected_data: Any):
        if not isinstance(expected_data, int):
            # 不正なデータ型の場合はTypeErrorを送出
            raise TypeError(
                f"[System Error] 評価データ型エラー (result_count): "
                f"期待する型=int, 実際の型={type(expected_data).__name__}"
            )
        super().__init__(expected_data)

    def evaluate(self, es_response: Dict[str, Any]) -> Tuple[bool, str]:
        total_hits, _ = self._get_hits_info(es_response)
        expected_count: int = self.expected_data  # 型チェック済み

        is_correct = total_hits == expected_count
        message = (
            f"正解！ヒット数: {total_hits}"
            if is_correct
            else f"不正解... ヒット数: {total_hits} (期待値: {expected_count})"
        )
        return is_correct, message
