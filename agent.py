from managed_deepagents import define_deep_agent
from tools.search import web_search

agent = define_deep_agent(
    name="devscope",
    model="google_genai:gemini-3.1-flash-lite",
    tools=[web_search]
)
