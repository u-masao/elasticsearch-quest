import asyncio
import os
import shutil

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from dotenv import load_dotenv

load_dotenv()


async def run(mcp_server: MCPServer):
    """エージェントの定義と実行"""
    agent = Agent(
        name="アシスタント",
        # エージェントへの指示 (自然言語)
        instructions="ユーザーのリクエストにしたがってElasticsearch を操作して",
        # 連携する MCP Server を指定
        mcp_servers=[mcp_server],
    )

    # 最初の命令
    message = "インデックス一覧を見せて"
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # 対話ループ
    while True:
        message = input("Elasticsearch で何がしたいですか？ > ")
        if message.lower() in ["exit", "quit"]:
            print("終了します。")
            break
        print(f"命令: {message}")
        result = await Runner.run(starting_agent=agent, input=message)
        print(result.final_output)


async def main():
    """メイン処理"""

    # MCPServerStdio を使って Elasticsearch MCP Server をサブプロセスとして起動・連携
    async with MCPServerStdio(
        name="MCP Elasticsearch",
        params={
            "command": "uv",  # MCP Server の実行コマンド (ここでは uv を使用)
            "args": [
                "--directory",
                "../elasticsearch-mcp-server",  # MCP Server のディレクトリ
                "run",
                "elasticsearch-mcp-server",  # MCP Server の実行ファイル/モジュール名
            ],
            # MCP Server に渡す環境変数 ( .env から読み込んだ Elasticsearch 接続情報)
            "env": {
                "ELASTICSEARCH_HOST": os.getenv("ELASTICSEARCH_URL"),
                "ELASTICSEARCH_USERNAME": os.getenv("ELASTICSEARCH_USERNAME"),
                "ELASTICSEARCH_PASSWORD": os.getenv("ELASTICSEARCH_PASSWORD"),
                "ELASTICSEARCH_CA_CERT": os.getenv("ELASTICSEARCH_CA_CERT"),
            },
        },
    ) as server:
        trace_id = gen_trace_id()
        # OpenAI Platform でトレースを確認するための設定
        with trace(workflow_name="MCP Elasticsearch", trace_id=trace_id):
            print(
                "トレース情報: https://platform.openai.com/traces/trace"
                f"?trace_id={trace_id}\n"
            )
            # エージェント実行ループを開始
            await run(server)


if __name__ == "__main__":
    # MCP Server 実行に必要な npx コマンドが存在するかチェック
    # elasticsearch-mcp-server が内部で npx を使う場合があるため
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx がインストールされていません。`npm install -g npx` "
            "コマンド等でインストールして下さい。"
        )

    asyncio.run(main())
