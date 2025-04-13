# src/evaluators/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class Evaluator(ABC):
    """評価ロジックの抽象基底クラス。"""

    def __init__(self, expected_data: Any):
        """
        Args:
            expected_data: クエストで定義された期待するデータ。
                           サブクラスはコンストラクタで適切な型チェックを行うべきです。
        """
        self.expected_data = expected_data

    @abstractmethod
    def evaluate(self, es_response: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Elasticsearchのレスポンスを評価し、結果とメッセージを返す。

        Args:
            es_response: Elasticsearchからのレスポンス。

        Returns:
            Tuple[bool, str]: (正解かどうか, 評価メッセージ)
        """
        raise NotImplementedError

    # --- Helper methods for subclasses ---
    @staticmethod
    def _get_hits_info(es_response: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
        """Elasticsearchレスポンスからヒット数とヒットリストを取得する。"""
        hits_info = es_response.get("hits", {})
        total_hits = hits_info.get("total", {}).get("value", 0)
        actual_hits_list = hits_info.get("hits", [])
        return total_hits, actual_hits_list

    @staticmethod
    def _get_aggregations(es_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Elasticsearchレスポンスから集計結果を取得する。"""
        return es_response.get("aggregations")
