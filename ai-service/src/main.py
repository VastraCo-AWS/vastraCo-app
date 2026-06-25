import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router, set_ai_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: validate that the Groq API key and model work before accepting traffic.
    The service marks itself unhealthy (via /health) if validation fails — keeps the
    container alive so logs remain accessible for diagnosis.
    """
    from src.groq_client import validate_groq_connectivity

    try:
        await validate_groq_connectivity()
        set_ai_status(healthy=True)
    except Exception as exc:
        logger.error(
            "⚠️  Groq validation failed at startup — AI responses will not work "
            "until this is resolved. Error: %s", exc
        )
        set_ai_status(healthy=False)

    yield  # service is running

    logger.info("AI service shutting down.")


app = FastAPI(
    title="VastraCo AI Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:80",
        "https://vastraco.online",
        "https://www.vastraco.online",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/ai")
