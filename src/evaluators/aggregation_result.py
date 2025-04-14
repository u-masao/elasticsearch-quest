# src/evaluators/aggregation_result.py
import json  # 複雑な比較のためにインポートする可能性あり
from typing import Any, Dict, Tuple

from .base import Evaluator


class AggregationResultEvaluator(Evaluator):
    """集計結果の内容で評価するクラス。"""

    def __init__(self, expected_data: Any):
        # expected_data は {"agg_name": "...", "expected_value": ...} 形式を期待
        if not isinstance(expected_data, dict):
            raise TypeError(
                f"[System Error] 評価データ型エラー (aggregation_result): "
                f"期待する型=dict, 実際の型={type(expected_data).__name__}"
            )
        if "agg_name" not in expected_data:
            # 必須キーがない場合はValueErrorを送出
            raise ValueError(
                "[System Error] aggregation_resultの評価データには"
                " 'agg_name' キーが必要です。"
            )
        # expected_value の型は多様なため、ここではチェックせず、evaluate内で扱う
        super().__init__(expected_data)

    def evaluate(self, es_response: Dict[str, Any]) -> Tuple[bool, str]:
        aggregations = self._get_aggregations(es_response)
        expected_agg_config: Dict[str, Any] = self.expected_data  # 型チェック済み

        if not aggregations:
            return (
                False,
                "不正解... レスポンスに集計結果 (`aggregations`) が含まれていません。",
            )

        expected_agg_name = expected_agg_config["agg_name"]
        expected_value = expected_agg_config.get("expected_value")  # 比較対象の値/構造

        actual_agg_result = aggregations.get(expected_agg_name)
        if actual_agg_result is None:
            return (
                False,
                f"不正解... 集計結果に '{expected_agg_name}' が見つかりません。",
            )

        # --- 集計結果の比較ロジック ---
        # この部分は `expected_value` の形式と `actual_agg_result` の構造に依存する
        # より汎用的な比較や、特定の集計タイプに特化した比較が必要な場合がある

        # 例1: 単純な値の比較 (e.g., Cardinality, Sum, Avg の .value)
        # expected_valueがスカラー値であると想定
        actual_simple_value = actual_agg_result.get("value")
        if actual_simple_value is not None and not isinstance(
            expected_value, (dict, list)
        ):
            is_correct = actual_simple_value == expected_value
            if is_correct:
                message = f"正解！集計 '{expected_agg_name}' の値が期待通り "
                f"({self._format_value(expected_value)}) です。"
            else:
                message = (
                    f"不正解... 集計 '{expected_agg_name}' の値が異なります。\n"
                    f"期待値: {self._format_value(expected_value)}\n"
                    f"実際の結果: {self._format_value(actual_simple_value)}"
                )
            return is_correct, message

        # 例2: バケットの比較 (e.g., Terms Aggregation)
        # expected_valueがリスト形式 (例: [{"key": ..., "doc_count": ...}, ...]) と想定
        actual_buckets = actual_agg_result.get("buckets")
        if isinstance(actual_buckets, list) and isinstance(expected_value, list):
            # TODO: より詳細なバケット比較ロジックを実装する
            #       (キーの存在、doc_countの一致、順序、特定のキー/値など)
            #       単純な全体比較は脆い可能性があるため注意
            is_correct = self._compare_structures(actual_buckets, expected_value)
            if is_correct:
                message = (
                    f"正解！集計 '{expected_agg_name}' の buckets が期待通りです。"
                )
            else:
                # 差分を表示するなど、より親切なメッセージが良い
                message = (
                    f"不正解... 集計 '{expected_agg_name}' の buckets が異なります。\n"
                    f"期待値: {self._format_value(expected_value)}\n"
                    f"実際の結果: {self._format_value(actual_buckets)}"
                )
            return is_correct, message

        # 例3: その他の構造比較 (集計結果の辞書全体を比較)
        # expected_value が辞書全体であると想定
        if isinstance(actual_agg_result, dict) and isinstance(expected_value, dict):
            is_correct = self._compare_structures(actual_agg_result, expected_value)
            if is_correct:
                message = f"正解！集計 '{expected_agg_name}' の構造全体が期待通りです。"
            else:
                message = (
                    f"不正解... 集計 '{expected_agg_name}' の構造全体が異なります。\n"
                    f"期待値: {self._format_value(expected_value)}\n"
                    f"実際の結果: {self._format_value(actual_agg_result)}"
                )
            return is_correct, message

        # 上記のいずれにも当てはまらない場合や、比較ロジックが不十分な場合
        return False, (
            f"[System Error] 集計 '{expected_agg_name}' の評価ロジックが未対応か、"
            f"期待値の形式 ({type(expected_value).__name__}) と"
            f"実際の集計結果の形式が一致しません。"
        )

    def _format_value(self, value: Any) -> str:
        """比較結果の表示用に値を整形するヘルパー"""
        if isinstance(value, (dict, list)):
            try:
                # JSON形式で見やすく整形
                return json.dumps(value, indent=2, ensure_ascii=False)
            except TypeError:
                return str(value)  # JSONシリアライズできない場合はそのまま文字列化
        return str(value)

    def _compare_structures(self, actual: Any, expected: Any) -> bool:
        """構造（リストや辞書）を比較するシンプルなヘルパー（必要に応じて拡張）"""
        # ここでは単純な同値比較を行う
        # より複雑な比較（順序無視、一部キーのみ比較など）が必要な場合は修正
        return actual == expected
