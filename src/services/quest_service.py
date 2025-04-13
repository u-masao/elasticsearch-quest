# src/services/quest_service.py
import json

from elasticsearch import ApiError, Elasticsearch, TransportError

# 依存モジュール
from ..db.quest_repository import Quest, QuestRepository
from ..exceptions import (
    QuestCliError,
    QuestNotFoundError,
)

# core_logic を利用する場合
from .core_logic import evaluate_result, execute_query, get_feedback

# または、評価ロジックなども Service 内に実装する


class QuestService:
    """クエストの取得、実行、評価を担当するサービスクラス"""

    def __init__(
        self, quest_repo: QuestRepository, es_client: Elasticsearch, index_name: str
    ):
        """
        Args:
            quest_repo: QuestRepositoryインスタンス.
            es_client: Elasticsearchクライアントインスタンス.
            index_name: 操作対象のElasticsearchインデックス名.
        """
        self.quest_repo = quest_repo
        self.es_client = es_client
        self.index_name = index_name

    def get_quest(self, quest_id: int) -> Quest:
        """
        指定されたIDのクエストを取得する。

        Args:
            quest_id: 取得するクエストのID.

        Returns:
            取得したQuestオブジェクト.

        Raises:
            QuestNotFoundError: 指定されたIDのクエストが見つからない場合.
        """
        quest = self.quest_repo.get_quest_by_id(quest_id)
        if not quest:
            raise QuestNotFoundError(f"クエストID {quest_id} が見つかりません。")
        return quest

    def execute_and_evaluate(
        self, quest: Quest, user_query_str: str
    ) -> tuple[bool, str, str | None, dict | None]:
        """
        ユーザーが提供したクエリを実行し、結果をルールベースで評価してフィードバックを生成する。

        Args:
            quest: 対象のQuestオブジェクト.
            user_query_str: ユーザーが入力したJSON形式のクエリ文字列.

        Returns:
            tuple: (正解かどうか, 評価メッセージ, ルールベースフィードバック, Elasticsearchレスポンス or None)

        Raises:
            ElasticsearchError: クエリ実行中にElasticsearch関連のエラーが発生した場合.
            InvalidQueryError: クエリ文字列のパースに失敗した場合 (通常は呼び出し元でチェック済み).
            QuestCliError: その他の予期せぬエラー.
        """
        attempt_count = 1  # 将来的に試行回数を記録・利用する場合は変更

        es_response: dict | None = None
        is_correct: bool = False
        eval_message: str = "評価エラー"
        feedback: str | None = None

        try:
            # execute_query は core_logic にある想定
            # TransportError, ValueError (JSONDecodeError含む), ElasticsearchException を捕捉
            es_response = execute_query(self.es_client, self.index_name, user_query_str)

            # 実行成功後、ルールベース評価
            is_correct, eval_message = evaluate_result(quest, es_response)
            feedback = get_feedback(quest, is_correct, attempt_count)

        except json.JSONDecodeError as e:
            # execute_query 内でパースする場合 or ここで再度パースする場合
            # 通常は load_query_from_source でチェック済みのはず
            is_correct = False
            eval_message = f"不正解... クエリのJSON形式が無効です: {e}"
            feedback = get_feedback(
                quest, is_correct=False, attempt_count=attempt_count
            )
            # エラーレスポンスはないので None を返す
            es_response = None
            # 必要であれば InvalidQueryError を raise しても良い
            # raise InvalidQueryError(f"クエリのJSON形式が無効です: {e}") from e

        except TransportError as e:
            # Elasticsearchへの接続エラー、クエリ構文エラーなど
            is_correct = False
            error_info = (
                e.info.get("error", {}).get("root_cause", [{}])[0].get("reason", str(e))
                if hasattr(e, "info")
                else str(e)
            )
            eval_message = f"不正解... クエリ実行エラー: {error_info}"
            feedback = get_feedback(
                quest, is_correct=False, attempt_count=attempt_count
            )
            es_response = None
            # エラーの詳細を返すために ElasticsearchError を raise する選択肢もある
            # raise ElasticsearchError(f"クエリ実行エラー: {error_info}") from e

        except ApiError as e:
            # TransportError 以外の Elasticsearch クライアントエラー
            is_correct = False
            eval_message = f"不正解... Elasticsearch関連エラー: {e}"
            feedback = get_feedback(
                quest, is_correct=False, attempt_count=attempt_count
            )
            es_response = None
            # raise ElasticsearchError(f"Elasticsearch関連エラー: {e}") from e

        except Exception as e:
            # core_logic内の予期せぬエラーなど
            # 予期せぬエラーは上位に伝播させる
            raise QuestCliError(
                f"クエリ実行または評価中に予期せぬエラーが発生しました: {e}"
            ) from e

        return is_correct, eval_message, feedback, es_response
