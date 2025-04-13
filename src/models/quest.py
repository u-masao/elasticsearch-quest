# src/models/quest.py
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Quest:
    """クエストデータを表現するデータクラス"""

    quest_id: int
    title: str
    description: str
    difficulty: int
    query_type_hint: Optional[str]
    evaluation_type: Literal[
        "result_count", "doc_ids_include", "doc_ids_in_order", "aggregation_result"
    ]
    evaluation_data_raw: str  # DBから取得した生の評価データ(JSON文字列など)
    hints_raw: Optional[str]  # DBから取得した生のヒント(JSON文字列など)
    created_at: str  # ISOフォーマット想定
    updated_at: str  # ISOフォーマット想定

    # パースされた評価データ (プロパティとしてアクセス)
    @property
    def evaluation_data(self) -> Any:
        """評価データを適切な型にパースして返す"""
        if self.evaluation_type == "result_count":
            try:
                return int(self.evaluation_data_raw)
            except (ValueError, TypeError):
                raise ValueError(
                    "指定の evaluation_data_raw が int にパースできません: "
                    f"{self.evaluation_data_raw}"
                )
        elif self.evaluation_type in [
            "doc_ids_include",
            "doc_ids_in_order",
            "aggregation_result",
        ]:
            try:
                return json.loads(self.evaluation_data_raw)
            except json.JSONDecodeError:
                raise ValueError(
                    "指定の evaluation_data_raw がJSONデコードできません: "
                    f"{self.evaluation_data_raw}"
                )
        else:
            # 他の評価タイプや未定義の場合は生データを返すかエラーにする
            raise ValueError(
                f"指定の evaluation_type はサポートしていません: {self.evaluation_type}"
            )

    # パースされたヒント (プロパティとしてアクセス)
    @property
    def hints(self) -> Optional[List[str]]:
        """ヒントを文字列のリストとして返す"""
        if self.hints_raw:
            try:
                hints_list = json.loads(self.hints_raw)
                if isinstance(hints_list, list) and all(
                    isinstance(h, str) for h in hints_list
                ):
                    return hints_list
                else:
                    # 想定外の形式ならNoneや空リストを返す
                    raise ValueError(f"hints_raw の形式が不正です: {self.hints_raw}")
            except json.JSONDecodeError:
                raise ValueError(
                    f"hints_raw がJSONデコードできません: {self.hints_raw}"
                )
        return []

    # dataclassから辞書への変換（必要であれば）
    def as_dict(self) -> Dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "query_type_hint": self.query_type_hint,
            "evaluation_type": self.evaluation_type,
            "evaluation_data": self.evaluation_data,  # パース済みデータを含む
            "hints": self.hints,  # パース済みデータを含む
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # 生データも必要なら含める
            # "evaluation_data_raw": self.evaluation_data_raw,
            # "hints_raw": self.hints_raw,
        }
