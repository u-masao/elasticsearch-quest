# src/evaluators/factory.py
from typing import Any, Dict, Type

from .aggregation_result import AggregationResultEvaluator
from .base import Evaluator
from .doc_ids_in_order import DocIdsInOrderEvaluator
from .doc_ids_include import DocIdsIncludeEvaluator
from .result_count import ResultCountEvaluator

# 他の評価クラスもインポート

# 評価タイプ文字列と評価クラスのマッピング
# 新しい評価タイプを追加したらここにも追記する
EVALUATOR_MAP: Dict[str, Type[Evaluator]] = {
    "result_count": ResultCountEvaluator,
    "doc_ids_include": DocIdsIncludeEvaluator,
    "doc_ids_in_order": DocIdsInOrderEvaluator,
    "aggregation_result": AggregationResultEvaluator,
}


def get_evaluator(eval_type: str, expected_data: Any) -> Evaluator:
    """
    評価タイプ文字列に対応するEvaluatorインスタンスを生成して返すファクトリ関数。

    Args:
        eval_type: 評価タイプ ("result_count", "doc_ids_include", etc.)。
        expected_data: クエストで定義された期待するデータ。

    Returns:
        対応するEvaluatorのインスタンス。

    Raises:
        ValueError: 未定義の評価タイプが指定された場合。
        TypeError: expected_data の型が評価クラスの期待と異なる場合 (コンストラクタで発生)。
        ValueError: expected_data の値が不正な場合 (コンストラクタで発生)。
    """
    evaluator_class = EVALUATOR_MAP.get(eval_type)
    if evaluator_class is None:
        # 未定義の評価タイプが指定された場合は ValueError を送出
        raise ValueError(f"[System Error] 未定義の評価タイプです: {eval_type}")

    try:
        # 対応する評価クラスをインスタンス化して返す
        # コンストラクタ内で型チェックや値チェックが行われる
        return evaluator_class(expected_data)
    except (TypeError, ValueError) as e:
        # Evaluatorのコンストラクタで発生したエラーをそのまま再送出
        # (エラーメッセージに詳細が含まれていることを期待)
        raise e
