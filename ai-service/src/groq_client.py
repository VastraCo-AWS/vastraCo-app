import logging

from langchain_groq import ChatGroq

from src.config import settings

logger = logging.getLogger(__name__)


async def validate_groq_connectivity() -> None:
    """Verify Groq API key and model are accessible before accepting traffic."""
    logger.info("Validating Groq connectivity — model: %s", settings.GROQ_MODEL)
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0,
        max_tokens=1,
    )
    await llm.ainvoke("ping")
    logger.info("✅ Groq connectivity OK — model '%s' is reachable.", settings.GROQ_MODEL)
