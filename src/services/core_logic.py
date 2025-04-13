# src/services/core_logic.py
import json
from typing import Any, Dict, Optional, Tuple

from elasticsearch import Elasticsearch, TransportError

# --- 依存関係 ---
# (これらのモジュール/クラスが存在することを前提とします)
from src.db.quest_repository import QuestRepository  # QuestRepositoryを想定
from src.evaluators.factory import get_evaluator  # 評価ファクトリをインポート
from src.models.quest import Quest  # Questモデルを想定


# execute_query 関数は元のままで良いでしょう
def execute_query(
    es_client: Elasticsearch, index_name: str, user_query_str: str
) -> Dict[str, Any]:
    """
    ユーザーが入力したJSON形式のクエリ文字列をElasticsearchで実行し、
    結果(レスポンス全体)を返す。
    (元のコードから変更なし)
    """
    try:
        # ユーザー入力をJSONとしてパース
        query_body = json.loads(user_query_str)
        if not isinstance(query_body, dict):
            raise ValueError("Query must be a JSON object.")

        print(f"\nExecuting query on index '{index_name}':")
        print(json.dumps(query_body, indent=2, ensure_ascii=False))

        # Elasticsearchにクエリを実行
        response = es_client.search(index=index_name, body=query_body)
        return response

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in query: {e}") from e
    except TransportError as e:
        # Elasticsearch固有のエラー (クエリ構文エラーなどを含む可能性)
        print(f"Elasticsearch query error details: {e.info}")  # エラー詳細を表示
        # エラー情報を付加して再送出するとデバッグしやすい場合がある
        raise TransportError(
            f"Elasticsearch query failed: {e.error}", e.info, e.status_code
        ) from e
    except Exception as e:
        print(f"An unexpected error occurred during query execution: {e}")
        raise  # その他の予期せぬエラー


def evaluate_result(quest: Quest, es_response: Dict[str, Any]) -> Tuple[bool, str]:
    """
    クエストの評価基準に基づき、Elasticsearchの実行結果を評価する。（リファクタリング版）
    評価ロジックは Evaluator クラス群に委譲する。

    Args:
        quest: 評価対象のQuestオブジェクト。
               `evaluation_type` (str) と `evaluation_data` (Any) を持つ想定。
        es_response: Elasticsearchからのレスポンス (dict)。

    Returns:
        Tuple[bool, str]: (正解かどうか, 評価メッセージ)
    """
    try:
        # Quest オブジェクトから評価タイプと期待データを取得
        eval_type = quest.evaluation_type
        # Questモデルが evaluation_data を適切な型で返すことを前提とします。
        # もしDB等にJSON文字列で保存されている場合は、Questモデル側か、
        # ここで json.loads() などでパースする必要があります。
        expected_data = quest.evaluation_data

        # ファクトリ関数を使って、評価タイプに対応する Evaluator インスタンスを取得
        evaluator = get_evaluator(eval_type, expected_data)

        # 取得した Evaluator オブジェクトの evaluate メソッドを呼び出して評価を実行
        is_correct, message = evaluator.evaluate(es_response)
        return is_correct, message

    except (ValueError, TypeError) as e:
        # get_evaluator や evaluator.evaluate で発生する可能性のあるエラー
        # (例: 未定義のeval_type、不正なexpected_data形式、評価中のエラー)
        # エラーメッセージはファクトリや各Evaluatorクラスで生成されることを期待
        error_message = f"評価設定または実行時エラー: {e}"
        print(error_message)  # ログ等にも出力推奨
        return False, error_message  # ユーザーフレンドリーなメッセージに加工しても良い
    except AttributeError as e:
        # Quest オブジェクトに必要な属性 (evaluation_type, evaluation_data)
        # がない場合など
        error_message = f"[System Error] Questオブジェクトの形式が不正です: {e}"
        print(error_message)
        return False, error_message
    except Exception as e:
        # その他の予期せぬエラー (Elasticsearchレスポンスの構造が想定外など)
        error_message = f"[System Error] 評価中に予期せぬエラーが発生しました: {e}"
        # 本番環境では、エラーの詳細をログに記録することが重要
        import traceback

        print(f"{error_message}\n{traceback.format_exc()}")
        return False, error_message


# get_feedback 関数は元のままで良いでしょう
# (依存している quest.hints の取得方法に合わせて調整が必要な場合があります)
def get_feedback(quest: Quest, is_correct: bool, attempt_count: int) -> str:
    """
    評価結果や試行回数に基づき、ユーザーへのフィードバック（ヒントなど）を生成する。
    (元のコードから変更なし、ただし quest.hints の取得方法に注意)
    """
    feedback = ""
    if not is_correct:
        feedback += "もう一度試してみましょう。\n"
        try:
            # Questモデルが hints をリスト (List[str]) として返すことを前提とします。
            # もしJSON文字列などで格納されている場合は、Questモデル側かここでパース
            # します。
            hints = quest.hints
            if hints and isinstance(hints, list):
                # 試行回数に応じてヒントを選択 (1-based index で扱う)
                hint_index = attempt_count - 1  # リストのインデックスは0-based
                if 0 <= hint_index < len(hints):
                    feedback += f"ヒント {attempt_count}: {hints[hint_index]}"
                elif hint_index >= len(hints) and hints:  # ヒントを使い切った場合
                    feedback += (
                        f"ヒント {len(hints)}: {hints[-1]} (これが最後のヒントです)"
                    )
                # else: attempt_count が 0 以下などの異常ケース
                # (最初のヒントを出すなど検討)
            else:
                feedback += "この問題には利用可能なヒントがありません。"
        except AttributeError:
            feedback += (
                "[System Error] Questオブジェクトからヒント情報を取得できませんでした。"
            )
        except Exception as e:
            # ヒント処理中の予期せぬエラー
            print(f"Error processing hints: {e}")
            feedback += "[System Error] ヒントの処理中にエラーが発生しました。"

    # 正解時の追加メッセージが必要であればここに記述
    # if is_correct:
    #    feedback += "\n素晴らしい！見事にクリアしました！"

    return feedback


# get_example_solution 関数は元のままで良いでしょう
# (依存している quest_repo の実装に合わせて調整が必要な場合があります)
def get_example_solution(quest_repo: QuestRepository, quest_id: int) -> Optional[str]:
    """
    指定されたクエストIDの解答例を取得する (DBに保存されている場合)。
    (元のコードから変更なし、ただし quest_repo のメソッド名に注意)
    """
    try:
        # QuestRepository に解答例取得メソッドが存在すると仮定
        # (メソッド名は実際のリポジトリ実装に合わせる)
        solution_json_str = quest_repo.get_solution_by_quest_id(quest_id)
        if solution_json_str:
            try:
                # JSON文字列をパースして整形して返す
                parsed_solution = json.loads(solution_json_str)
                return json.dumps(parsed_solution, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # パースできない場合 (JSON形式でない場合など) はそのまま返す
                return solution_json_str
        return None  # 解答例が見つからない場合は None を返す
    except AttributeError:
        # QuestRepository に指定のメソッドがない場合
        print(
            "Error: QuestRepository instance lacks 'get_solution_by_quest_id' method."
        )
        # ユーザーにはシステムエラーとして伝えるのが適切か検討
        return "[System Error] 解答例取得機能が利用できません。"
    except Exception as e:
        # DB接続エラーなど、解答例取得中のその他のエラー
        print(f"Error fetching example solution for quest_id {quest_id}: {e}")
        return "[System Error] 解答例の取得中にエラーが発生しました。"


# generate_example_solution_with_llm 関数は元のままで良いでしょう
# (具体的な実装は別途必要)
def generate_example_solution_with_llm(quest: Quest) -> str:
    """(将来実装) LLMを使ってクエストの解答例を生成する"""
    # ここにLLM API呼び出しなどのロジックを実装
    raise NotImplementedError("LLMによる解答例生成は未実装です。")
