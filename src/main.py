from agents import Agent, Runner
from dotenv import load_dotenv

load_dotenv()

sample_agent = Agent(
    name="hello agent",
    instructions="常に挨拶します",
)


def main():
    result = Runner.run_sync(sample_agent, input="最近どう？")
    print(result.final_output)


if __name__ == "__main__":
    main()
