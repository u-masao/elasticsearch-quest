# src/view.py
import json

import click

from .db.quest_repository import Quest  # Questモデルをインポート
from .exceptions import InvalidQueryError


class QuestView:
    """CLIへの出力を担当するクラス"""

    def display_quest_details(self, quest: Quest):
        """クエストの詳細情報を表示する"""
        title_line = f"--- クエスト {quest.quest_id}: {quest.title} ---"
        click.echo(click.style(title_line, fg="cyan", bold=True))
        click.echo(f"難易度: {quest.difficulty}")
        click.echo(f"内容:\n{quest.description}")  # 内容は改行される可能性を考慮
        click.echo("-" * len(title_line))

    def display_elasticsearch_response(self, response: dict | None):
        """Elasticsearchからのレスポンス（一部）を表示する"""
        if response is None:
            click.echo(click.style("\n--- Elasticsearch Response ---", bold=True))
            click.echo("(レスポンスなし)")
            click.echo("-" * 30)
            return

        click.echo(click.style("\n--- Elasticsearch Response (Hits) ---", bold=True))
        hits_info = response.get("hits", {})
        total_hits = hits_info.get("total", {}).get("value", "N/A")
        click.echo(f"Total Hits: {total_hits}")

        hits = hits_info.get("hits", [])
        if hits:
            click.echo("Documents (first 3):")
            for i, hit in enumerate(hits[:3]):
                doc_id = hit.get("_id", "N/A")
                score = hit.get("_score", "N/A")
                source = hit.get("_source", {})
                # ソースの内容を簡潔に表示 (例: nameやtitleなど代表的なフィールド)
                source_summary = ", ".join(
                    f"{k}: {v}" for k, v in list(source.items())[:2]
                )  # 最初の2項目
                click.echo(
                    f"  {i + 1}. ID: {click.style(str(doc_id), fg='yellow')}, "
                    f"Score: {click.style(str(score), fg='blue')}, "
                    f"Source: {{{source_summary}}}"
                )
        else:
            click.echo("Documents: (No hits)")

        if "aggregations" in response:
            click.echo(
                click.style(
                    "\n--- Elasticsearch Response (Aggregations) ---", bold=True
                )
            )
            click.echo(
                json.dumps(response["aggregations"], indent=2, ensure_ascii=False)
            )
        click.echo("-" * 30)

    def display_evaluation(self, message: str, is_correct: bool):
        """評価結果を表示する"""
        click.echo(click.style("\n--- 評価 ---", bold=True))
        color = "green" if is_correct else "red"
        click.echo(click.style(message, fg=color))
        click.echo("-" * 12)

    def display_feedback(self, feedback_title: str, feedback: str | None):
        """フィードバックを表示する"""
        if feedback:
            # 複数行のフィードバックを考慮してインデントなどを調整してもよい
            click.echo(click.style(f"\n--- {feedback_title} ---", bold=True))
            click.echo(feedback)
            click.echo("-" * (len(feedback_title) + 6))

    def display_error(self, message: str):
        """汎用エラーメッセージを表示する"""
        click.secho(f"エラー: {message}", fg="red", err=True)

    def display_warning(self, message: str):
        """警告メッセージを表示する"""
        click.secho(f"警告: {message}", fg="yellow", err=True)

    def display_info(self, message: str):
        """情報メッセージを表示する"""
        click.echo(message)

    def display_trace_info(self, trace_id: str):
        """トレース情報へのリンクを表示"""
        url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
        self.display_info(f"Trace URL: {url}")

    def display_clear_message(self):
        """クエストクリアメッセージを表示する"""
        click.secho(
            "\n🎉 クエストクリア！おめでとうございます！ 🎉", fg="green", bold=True
        )

    def display_retry_message(self):
        """再挑戦を促すメッセージ"""
        click.secho(
            "\n残念、不正解です。フィードバックを参考に、もう一度挑戦してみましょう。",
            fg="yellow",
        )

    def prompt_for_query(self) -> str:
        """対話的にクエリ入力を求める"""
        click.echo(
            click.style(
                "\nElasticsearchクエリをJSON形式で入力してください (Ctrl+D or Ctrl+Z+Enter で終了):",
                fg="blue",
            )
        )
        lines = []
        while True:
            try:
                # 標準入力がリダイレクトされている場合なども考慮すると、click.get_text_stream('stdin') を使う方が堅牢
                line = input()
                lines.append(line)
            except EOFError:
                break
        query = "\n".join(lines).strip()
        if not query:
            raise InvalidQueryError("入力されたクエリが空です。")
        return query
