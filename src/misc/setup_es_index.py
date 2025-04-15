import asyncio
import os
import shutil

import click
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from dotenv import load_dotenv

load_dotenv()


async def run(
    mcp_server: MCPServer,
    index_name: str,
    input_filepath: str,
):
    """エージェントの定義と実行"""
    agent = Agent(
        name="アシスタント",
        # エージェントへの指示 (自然言語)
        instructions="ユーザーのリクエストにしたがってElasticsearch を操作して",
        # 連携する MCP Server を指定
        mcp_servers=[mcp_server],
    )

    # インデックスの作成とデータの投入
    data = open(input_filepath, "r").read()
    message = f"""
    次のデータを投入するインデックスを作って。
    インデックス名は {index_name} です。
    すでにインデックスがある場合は、一度消してから上書きして。

    - metric_vector フィールドは L2 距離でベクトル検索します
      - index_options は "type":"hnsw" として
    - アイテムの ID は、1 から連番とします
    - publisher フィールドは、publisher.keyword も作って

    <data>
    {data}
    </data>
    """
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(f"応答: {result.final_output}")

    # データの確認
    message = f"""
    {index_name} インデックスのドキュメントの件数を教えて
    """
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(f"応答: {result.final_output}")

    # データの確認
    message = f"""
    インデックス名: {index_name}

    publisher フィールドが "オライリー" に部分一致するものを列挙して
    """
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(f"応答: {result.final_output}")

    # データの確認
    message = f"""
    インデックス名: {index_name}

    metric_vector フィールドが [5,6] に近い順にベクトル検索で列挙して
    metric_vecto[0] は Technical Score
    metric_vecto[1] は Mathematical Score

    結果にはL2距離も含めて
    """
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(f"応答: {result.final_output}")

    # ダンプ
    message = f"""
    インデックス名: {index_name}

    1. まずこのインデックスのスキーマとデータ20件を確認して。

    2. そしてこのインデックスを作るための CURL コマンドを作成して。

    - インデックス削除
    - インデックス作成と Maping 設定
      - 特にベクトルフィールドに注意
    - データ投入20件すべて
    - 簡単なデータ確認
    """
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(f"応答: {result.final_output}")


async def main(index_name: str, input_filepath: click.Path):
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
            await run(server, index_name, input_filepath)


@click.command()
@click.argument("index_name", type=str)
@click.argument("input_filepath", type=click.Path(exists=True))
def cli(**kwargs):
    asyncio.run(
        main(
            kwargs["index_name"],
            kwargs["input_filepath"],
        )
    )


if __name__ == "__main__":
    # MCP Server 実行に必要な npx コマンドが存在するかチェック
    # elasticsearch-mcp-server が内部で npx を使う場合があるため
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx がインストールされていません。`npm install -g npx` "
            "コマンド等でインストールして下さい。"
        )
    cli()
