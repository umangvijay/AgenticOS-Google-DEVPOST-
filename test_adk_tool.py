import asyncio
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner

def get_current_time(timezone: str = "UTC") -> str:
    """Returns the current time for a given timezone."""
    return "2026-08-22 21:00:00 UTC"

async def main():
    agent = LlmAgent(name="TimeAgent", instruction="You are a helpful time assistant.", model="gemini-3.5-flash", tools=[get_current_time])
    runner = Runner(agent=agent, app_name="test_app", auto_create_session=True)
    try:
        events = await runner.run_debug("What time is it in UTC?")
        for e in events:
            print(e)
    except Exception as ex:
        print("Error:", ex)

asyncio.run(main())
