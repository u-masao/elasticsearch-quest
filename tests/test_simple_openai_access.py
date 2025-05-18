import pytest
from agents import Agent, Runner
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.asyncio
async def test_simple_openai_access():
    agent = Agent(name="sample agent", instructions="最小限の文字数で応答して")

    result = await Runner.run(agent, input="最近どう？")

    print(result)

    assert result is not None
    assert len(result.final_output)
