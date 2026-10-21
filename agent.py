from managed_deepagents import define_deep_agent
from langchain.agents.middleware import ModelCallLimitMiddleware,ToolCallLimitMiddleware,PIIMiddleware


agent = define_deep_agent(
    name="devscope",
    model="google_genai:gemini-3.1-flash-lite",
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
            exit_behavior="end",
        ),
        ToolCallLimitMiddleware(
            thread_limit=20, 
            run_limit=10,
            exit_behavior="end"
        ),
        PIIMiddleware(
            "email",
            strategy="redact", 
            apply_to_input=True
        ),
        PIIMiddleware(
            "credit_card", 
            strategy="mask", 
            apply_to_input=True
        ),
    ]
)
