import asyncio
import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner

project = os.getenv('GOOGLE_CLOUD_PROJECT', 'agentos-test')

def get_current_time(timezone: str = 'UTC') -> str:
    return '2026-08-22 21:00:00 UTC'

async def main():
    try:
        llm = Gemini(name='gemini-3.5-flash', client_kwargs={"vertexai": True, "project": project, "location": "us-central1"})
        agent = LlmAgent(name='TimeAgent', instruction='You are a helpful time assistant.', model=llm, tools=[get_current_time])
        runner = InMemoryRunner(agent=agent, app_name='test_app')
        events = await runner.run_debug('What time is it in UTC?')
        for e in events:
            print(e)
    except Exception as ex:
        print('Error:', type(ex), ex)

asyncio.run(main())
