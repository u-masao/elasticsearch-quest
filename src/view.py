# src/view.py
import json

import click

from .db.quest_repository import Quest  # Questモデルをインポート


class EndOfMessage:
    pass


class QuestView:
    """CLIへの出力を担当するクラス"""

    def __init__(self, echo_function=None):
        """Initialize with a custom echo function if provided."""
        self.custom_echo = echo_function or self.default_echo

    async def default_echo(
        self,
        message: str | EndOfMessage,
        fg: str = None,
        bold: bool = False,
        err: bool = False,
    ):
        """Default echo function using click."""
        if not isinstance(message, EndOfMessage):
            click.echo(click.style(message, fg=fg, bold=bold), err=err)

    async def close(self):
        """表示セッションを終了"""
        await self.custom_echo(EndOfMessage())

    async def display_quest_details(self, quest: Quest):
        """クエストの詳細情報を表示する"""
        title_line = f"## クエスト {quest.quest_id}: {quest.title}"
        await self.custom_echo(title_line)
        await self.custom_echo(f"難易度: {quest.difficulty}")
        await self.custom_echo(
            f"内容:\n{quest.description}\n\n"
        )  # 内容は改行される可能性を考慮

    async def display_elasticsearch_response(self, response: dict | None):
        """Elasticsearchからのレスポンス（一部）を表示する"""
        await self.custom_echo("## Elasticsearch Response")
        if response is None:
            await self.custom_echo("(レスポンスなし)")
            return

        hits_info = response.get("hits", {})
        total_hits = hits_info.get("total", {}).get("value", "N/A")
        await self.custom_echo(f"Total Hits: {total_hits}")

        hits = hits_info.get("hits", [])

        if hits:
            await self.custom_echo("Documents (first 3):")
            for i, hit in enumerate(hits[:3]):
                doc_id = hit.get("_id", "N/A")
                score = hit.get("_score", "N/A")
                source = hit.get("_source", {})

                source_summary = ", ".join(f"{k}: {v}" for k, v in source.items())
                await self.custom_echo(
                    f"- ranking: {i + 1}, "
                    f"ID: {doc_id}, "
                    f"Score: {score}, "
                    f"Source: {{{source_summary}}}"
                )
        else:
            await self.custom_echo("- Documents: (No hits)")

        if "aggregations" in response:
            await self.custom_echo("## Elasticsearch Response (Aggregations)")
            await self.custom_echo(
                json.dumps(response["aggregations"], indent=2, ensure_ascii=False)
            )

    async def display_evaluation(self, message: str, is_correct: bool):
        """評価結果を表示する"""
        await self.custom_echo("## 評価")
        icon = "🎉🎉🎉🎉" if is_correct else "😿😿😿😿"
        await self.custom_echo(message + icon)

    async def display_feedback(self, feedback_title: str, feedback: str | None):
        """フィードバックを表示する"""
        if feedback:
            # 複数行のフィードバックを考慮してインデントなどを調整してもよい
            await self.custom_echo(f"## {feedback_title}")
            await self.custom_echo(feedback)

    async def display_error(self, message: str):
        """汎用エラーメッセージを表示する"""
        await self.custom_echo(f"エラー: {message}", fg="red", err=True)

    async def display_warning(self, message: str):
        """警告メッセージを表示する"""
        await self.custom_echo(f"警告: {message}", fg="yellow", err=True)

    async def display_info(self, message: str):
        """情報メッセージを表示する"""
        await self.custom_echo(message)

    async def display_trace_info(self, trace_id: str):
        """トレース情報へのリンクを表示"""
        url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
        await self.display_info(f"Trace URL: {url}")

    async def display_clear_message(self):
        """クエストクリアメッセージを表示する"""
        await self.custom_echo("🎉 クエストクリア！おめでとうございます！ 🎉")

    async def display_retry_message(self):
        """再挑戦を促すメッセージ"""
        await self.custom_echo(
            "残念、不正解です。フィードバックを参考に、もう一度挑戦してみましょう。"
        )
