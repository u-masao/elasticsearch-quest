# src/utils/query_loader.py
import json
from pathlib import Path
from typing import Callable

from ..exceptions import InvalidQueryError


def load_query_from_source(
    query_str: str | None,
    query_file: Path | None,
    prompt_func: Callable[[], str] | None = None,
) -> str:
    """
    ファイル、文字列、または対話入力からクエリ文字列を取得し、JSON形式か検証する。

    Args:
        query_str: クエリ文字列 (CLI引数).
        query_file: クエリファイルパス (CLI引数).
        prompt_func: 対話入力が必要な場合に呼び出す関数.

    Returns:
        有効なJSON形式のクエリ文字列.

    Raises:
        InvalidQueryError: クエリの取得や検証に失敗した場合.
        FileNotFoundError: クエリファイルが見つからない or 読み込めない場合.
    """
    user_query_str = None
    source = "不明"

    if query_file:
        source = f"ファイル '{query_file}'"
        try:
            user_query_str = query_file.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"クエリファイルが見つかりません: {query_file}"
            ) from e
        except Exception as e:
            # パーミッションエラーなども考慮
            raise InvalidQueryError(
                f"クエリファイル '{query_file}' の読み込みに失敗しました: {e}"
            ) from e
    elif query_str:
        source = "コマンドライン引数 (--query)"
        user_query_str = query_str
    elif prompt_func:
        source = "対話入力"
        # prompt_func内でEOFErrorや空入力はInvalidQueryErrorとして処理される想定
        user_query_str = prompt_func()
    else:
        # どのソースも指定されていない場合
        raise InvalidQueryError(
            "クエリのソースが指定されていません (--query または "
            "--query-file を使用するか、対話モードで入力してください)。"
        )

    if not user_query_str or not user_query_str.strip():
        raise InvalidQueryError(f"{source} から取得されたクエリが空です。")

    # 簡単なJSON形式チェック
    try:
        json.loads(user_query_str)
    except json.JSONDecodeError as e:
        raise InvalidQueryError(
            f"{source} から取得されたクエリが有効なJSON形式ではありません: {e}"
        ) from e

    return user_query_str
