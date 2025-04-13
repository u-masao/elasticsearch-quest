# main_cli.py
import os
import argparse
import json
from pathlib import Path
import sys
from elasticsearch import TransportError


# プロジェクトルートをパスに追加（srcなどをインポートするため）
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 必要なモジュールをインポート
from src.db.quest_repository import QuestRepository
from src.elasticsearch_client import get_es_client
from src.core_logic import (
    execute_query,
    evaluate_result,
    get_feedback,
)

# フィクスチャファイルのパスを定義
FIXTURES_DIR = Path("fixtures")
SCHEMA_FILE = FIXTURES_DIR / "create_quests_table.sql"
DATA_FILE = FIXTURES_DIR / "insert_quests.sql"

# --- 設定 ---
# QuestRepositoryが使うDBファイルのパス (設定可能にする)
DB_FILE_PATH = "data/quests.db"
# Elasticsearchインデックス名
INDEX_NAME = "sample_books"


def main():
    parser = argparse.ArgumentParser(description="Elasticsearch Quest CLI")
    parser.add_argument("quest_id", type=int, help="挑戦するクエストのID")
    parser.add_argument(
        "--query", type=str, help="実行するElasticsearchクエリ (JSON文字列)"
    )
    parser.add_argument(
        "--query-file",
        type=str,
        help="実行するElasticsearchクエリが書かれたJSONファイルパス",
    )
    # parser.add_argument("--show-solution", action="store_true", help="指定したクエストの解答例を表示する") # 解答例機能実装後

    args = parser.parse_args()

    # --- 初期化 ---
    try:
        quest_repo = QuestRepository(DB_FILE_PATH)
        if not Path(DB_FILE_PATH).exists():
            quest_repo.initialize_schema(SCHEMA_FILE)
            quest_repo.load_data(DATA_FILE)
    except Exception as e:
        print(f"初期化エラー: {e}", file=sys.stderr)
        sys.exit(1)

    # --- クエスト情報取得 ---
    quest = quest_repo.get_quest_by_id(args.quest_id)
    if not quest:
        print(f"エラー: クエストID {args.quest_id} が見つかりません。", file=sys.stderr)
        sys.exit(1)

    print(f"--- クエスト {quest.quest_id}: {quest.title} ---")
    print(f"難易度: {quest.difficulty}")
    print(f"内容: {quest.description}")
    print("-" * (len(f"--- クエスト {quest.quest_id}: {quest.title} ---")))

    # --- 解答例表示 (オプションが有効な場合) ---
    # if args.show_solution:
    #     solution = get_example_solution(quest_repo, args.quest_id) # 仮の関数呼び出し
    #     if solution:
    #         print("\n--- 解答例 ---")
    #         print(solution)
    #         print("-" * 15)
    #     else:
    #         print("\nこのクエストの解答例は利用できません。")
    #     sys.exit(0) # 解答例を表示したら終了

    # --- クエリ取得 ---
    user_query_str = None
    if args.query:
        user_query_str = args.query
    elif args.query_file:
        try:
            with open(args.query_file, "r", encoding="utf-8") as f:
                user_query_str = f.read()
        except FileNotFoundError:
            print(
                f"エラー: クエリファイルが見つかりません: {args.query_file}",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(
                f"エラー: クエリファイルの読み込みに失敗しました: {e}", file=sys.stderr
            )
            sys.exit(1)
    else:
        # クエリが指定されなかった場合は、インタラクティブに入力を促す (改良案)
        print(
            "\nElasticsearchクエリをJSON形式で入力してください (Ctrl+D または空行で終了):"
        )
        lines = []
        try:
            while True:
                line = input()
                if not line:  # 空行で終了
                    break
                lines.append(line)
        except EOFError:  # Ctrl+Dで終了
            pass
        user_query_str = "\n".join(lines)
        if not user_query_str:
            print("エラー: クエリが入力されませんでした。", file=sys.stderr)
            sys.exit(1)

    # --- クエリ実行 ---
    try:
        es_client = get_es_client()
        es_response = execute_query(es_client, INDEX_NAME, user_query_str)
        print("\n--- Elasticsearch Response (Hits) ---")
        # レスポンスの一部を表示 (デバッグ用)
        hits_info = es_response.get("hits", {})
        print(f"Total Hits: {hits_info.get('total', {}).get('value', 'N/A')}")
        print("Documents (first few):")
        for i, hit in enumerate(hits_info.get("hits", [])[:3]):  # 上位3件表示
            print(
                f"  {i + 1}. ID: {hit.get('_id')}, Score: {hit.get('_score')}, Source: {hit.get('_source', {}).get('name', 'N/A')}"
            )
        if "aggregations" in es_response:
            print("\n--- Elasticsearch Response (Aggregations) ---")
            print(json.dumps(es_response["aggregations"], indent=2, ensure_ascii=False))
        print("-" * 30)

    except (ValueError, TransportError) as e:
        print(f"\nクエリエラー: {e}", file=sys.stderr)
        # 不正解として扱うか、ここで終了するか選択
        print("\n--- 評価 ---")
        print("不正解... クエリの実行中にエラーが発生しました。")
        print("-" * 12)
        # ヒントを表示する (エラー内容に基づいてヒントを出すことも可能)
        feedback = get_feedback(
            quest, is_correct=False, attempt_count=1
        )  # エラー時は試行1回目扱い
        if feedback:
            print("\n--- フィードバック ---")
            print(feedback)
            print("-" * 18)
        sys.exit(1)  # エラーで終了
    except Exception as e:
        print(f"\n予期せぬエラー: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 結果評価 ---
    # 試行回数を管理する仕組みがまだないため、仮に1回目とする
    attempt_count = 1
    is_correct, eval_message = evaluate_result(quest, es_response)

    print("\n--- 評価 ---")
    print(eval_message)
    print("-" * 12)

    # --- フィードバック表示 ---
    feedback = get_feedback(quest, is_correct, attempt_count)
    if feedback:
        print("\n--- フィードバック ---")
        print(feedback)
        print("-" * 18)

    if is_correct:
        print("\nクエストクリア！おめでとうございます！")
        # 次のクエストへ進む処理などを将来的に追加
    else:
        # 再挑戦を促すメッセージなど
        pass


if __name__ == "__main__":
    # 実行前に環境変数 ELASTICSEARCH_URL などが設定されているか確認
    if "ELASTICSEARCH_URL" not in os.environ and "ELASTIC_CLOUD_ID" not in os.environ:
        print(
            "警告: 環境変数 ELASTICSEARCH_URL または ELASTIC_CLOUD_ID が設定されていません。",
            file=sys.stderr,
        )
        print("デフォルトの http://localhost:9200 に接続を試みます。", file=sys.stderr)
    main()
