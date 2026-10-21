from collections.abc import Awaitable, Callable

from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command


@wrap_tool_call
async def log_tool_calls(
    request: ToolCallRequest,
    handler: Callable[
        [ToolCallRequest],
        Awaitable[ToolMessage | Command],
    ],
) -> ToolMessage | Command:
    tool_name = request.tool_call["name"]

    print(f"Calling tool: {tool_name}")

    try:
        result = await handler(request)
    except Exception:
        print(f"Tool failed: {tool_name}")
        raise

    print(f"Finished tool: {tool_name}")
    return result