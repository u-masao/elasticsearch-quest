import textwrap
from typing import Any, Optional

import click
from agents import (
    Agent,
    RunContextWrapper,
    RunHooks,
    Runner,
    Tool,
    Usage,
    gen_trace_id,
    trace,
)
from dotenv import load_dotenv

load_dotenv()


class ExampleHooks(RunHooks):
    def __init__(self):
        self.event_counter = 0

    def _usage_to_str(self, usage: Usage) -> str:
        return (
            f"{usage.requests} requests, {usage.input_tokens} input tokens, "
            f"{usage.output_tokens} output tokens, {usage.total_tokens} total tokens"
        )

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Agent {agent.name} started. Usage: "
            f"{self._usage_to_str(context.usage)}"
        )

    async def on_agent_end(
        self, context: RunContextWrapper, agent: Agent, output: Any
    ) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Agent {agent.name} ended with output "
            f"{output}. Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_tool_start(
        self, context: RunContextWrapper, agent: Agent, tool: Tool
    ) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Tool {tool.name} started. Usage: "
            f"{self._usage_to_str(context.usage)}"
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Tool {tool.name} ended with result "
            f"{result}. Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_handoff(
        self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Handoff from {from_agent.name} to "
            f"{to_agent.name}. Usage: {self._usage_to_str(context.usage)}"
        )


hooks = ExampleHooks()


class BookGenerator:
    def __init__(self, model: Optional[str] = "o3-mini"):
        self.model = model
        pass

    def _make_agent(self, name: str, instructions: str, model: Optional[str]):
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model if model is not None else "o3-mini",
        )
        return self.agent

    def run(self):
        history = []
        trace_id = gen_trace_id()
        domain_info = "Elasticsearch 8.17"

        instructions = f"""
            あなたは優秀な {domain_info} のエキスパートです。
            ユーザーの指示にしたがって考え抜かれた応答をして下さい。
        """
        with trace(workflow_name="generate book", trace_id=trace_id):
            for prompt in self.prompt_flow():
                history += [{"role": "user", "content": prompt}]
                result = Runner.run_sync(
                    self._make_agent(
                        name="assistant",
                        instructions=instructions,
                        model=self.model,
                    ),
                    input=history,
                    hooks=hooks,
                )
                history = result.to_input_list()
        return result

    def prompt_flow(self):
        plan = open("docs/PLAN.md", "r").read()
        exam_theme = "日本のデータサイエンティストが好きそうな書籍"
        data_size = 50
        chapter_size = 10
        quests_par_chapter_size = 10
        yield textwrap.dedent(f"""
            # plan

            以下の計画で利用するデータを作成します。

            <plan>
            {plan}
            </plan>

            # make loadmap

            問題集の形式で Elasticsearch の検索クエリの作り方を学ぶ
            教材を作ります。基本的なクエリから、ベクトル検索、ハイブ
            リッドベクトル検索までの loadmap を作って。
            chapter を {chapter_size} 程度に分割して徐々にステップアップするように。
            すべての chapter でクエリを作成して結果を確認する演習問題
            ができるようにして。
            それぞれの chapter で学習内容を箇条書きで詳しく書いて。
            構文例や問題の例は不要。検索クエリの作り方について学ぶの
            で、mapping の設定、トラブルシューティング、冗長化、
            性能チューニングは不要。

            # make sample data
            先程の loadmap に従って演習を行います。
            演習に必要な sample data と mapping を作って。
            テーマは「{exam_theme}」です。
            演習問題で必要になりそうな幅広い種類のカラムを作って。
            dense_vector は 2 次元にして。
            件数は{data_size}件ね。

            # make quests
            sample data を利用した quest (演習問題)を作って。
            Quest は回答が一意に決まるように十分な情報をユーザーに
            提示して下さい。目的のフィールド名、検索の方式、
            しきい値等の具体的な値、検索で抽出したい文字列、
            前方一致、完全一致等です。

            quest には、quest_id, chapter_id, title, description,
            query_type_hint, evaluation_method, evaluation_data,
            hint, difficultry[int] を含めて下さい。
            他に必要なカラムがあれば追加して下さい。
            Quest は、Chapter 毎に {quests_par_chapter_size} 個づつ用意して下さい。

            評価方法は、result_count、doc_ids_include、
            doc_ids_in_order、doc_ids_in_order に対応しています。

            # output
            loadmap, mapping, sample data, quest を一つの
            JSONオブジェクトにして出力して下さい。
            絶対に件数を省略せずに、すべての情報を出力して下さい。
            JSON内にはコメントとか説明は一切書かないで、厳格な
            JSON形式にしたがって。
            内容は日本語で。
        """)


@click.command()
@click.argument("output_filepath", type=click.Path())
def main(output_filepath):
    book_generator = BookGenerator()
    result = book_generator.run()
    print(result.final_output)
    open(output_filepath, "w").write(result.final_output)


if __name__ == "__main__":
    main()
