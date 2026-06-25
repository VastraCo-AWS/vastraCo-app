import json
import logging
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.config import settings
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.tools import create_tools

logger = logging.getLogger(__name__)

# ── LLM singleton ────────────────────────────────────────────────────────────
_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model=settings.GROQ_MODEL,
    temperature=0.1,
    max_tokens=1024,
)

# ── Conversation memory ───────────────────────────────────────────────────────
# Shared across all sessions — keyed by thread_id (= session_id from the client).
# Lives in RAM; cleared on service restart.
_memory = MemorySaver()


async def run_agent_session(
    session_id: str,
    user_message: str,
    user_token: Optional[str] = None,
) -> dict:
    """
    Invoke the LangGraph ReAct agent for one turn in a session.

    Tools are re-bound per request because the set of available tools depends on
    whether the user is authenticated (order tools require a JWT).

    Returns {"response": str, "products": list[dict]}.
    """
    tools = create_tools(
        product_service_url=settings.PRODUCT_SERVICE_URL,
        order_service_url=settings.ORDER_SERVICE_URL,
        user_token=user_token,
    )

    graph = create_react_agent(
        model=_llm,
        tools=tools,
        checkpointer=_memory,
        prompt=SYSTEM_PROMPT,
    )

    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )

    messages = result.get("messages", [])
    if not messages:
        return {
            "response": "Sorry, I couldn't process your request. Please try again.",
            "products": [],
        }

    # Groq returns plain string content — no content blocks or thinking tags
    final = messages[-1]
    ai_text = final.content if isinstance(final.content, str) else str(final.content)

    # Extract product results from the most recent search_products tool call
    products = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content)
                if isinstance(data, dict) and data.get("products"):
                    products = data["products"][:6]
                    break
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

    return {"response": ai_text, "products": products}
