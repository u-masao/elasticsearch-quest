from agents import Agent, Runner
from dotenv import load_dotenv

load_dotenv()


def test_simple_openai_access():
    agent = Agent(name="sample agent", instructions="最小限の文字数で応答して")

    result = Runner.run_sync(agent, input="最近どう？")

    assert result is not None
    assert len(result.final_output)
