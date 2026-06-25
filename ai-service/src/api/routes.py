import logging
from typing import Optional

import jwt as pyjwt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.config import settings
from src.agent.graph import run_agent_session

router = APIRouter()
logger = logging.getLogger(__name__)

# Set by main.py lifespan after startup validation completes
_ai_healthy: bool = False


def set_ai_status(healthy: bool) -> None:
    """Called from main.py lifespan to record Groq validation result."""
    global _ai_healthy
    _ai_healthy = healthy


class ChatRequest(BaseModel):
    message: str
    session_id: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        if len(v) > 2000:
            raise ValueError("message too long (max 2000 characters)")
        return v

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id is required")
        return v.strip()


def _extract_user_token(request: Request) -> Optional[str]:
    """Extract JWT from cookie or Authorization header and validate signature."""
    token = request.cookies.get("token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()

    if not token or not settings.JWT_SECRET:
        return None

    try:
        pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return token
    except pyjwt.PyJWTError:
        return None


@router.get("/health")
async def health():
    return {
        "status": "ok" if _ai_healthy else "degraded",
        "service": "ai-service",
        "provider": "groq",
        "groq": "connected" if _ai_healthy else "unavailable",
        "model": settings.GROQ_MODEL,
    }


@router.get("/ready")
async def ready():
    if not _ai_healthy:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Groq connectivity unavailable"},
        )
    return {"status": "ready"}


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    if not _ai_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "error": "AI service is not ready — Groq connectivity could not be verified at startup. "
                         "Check GROQ_API_KEY and GROQ_MODEL in Secrets Manager.",
                "session_id": body.session_id,
            },
        )

    user_token = _extract_user_token(request)

    try:
        result = await run_agent_session(
            session_id=body.session_id,
            user_message=body.message,
            user_token=user_token,
        )
        return {
            "response": result["response"],
            "products": result.get("products", []),
            "session_id": body.session_id,
            "authenticated": user_token is not None,
        }
    except Exception as e:
        logger.error("Chat error for session %s: %s", body.session_id, e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "AI assistant is temporarily unavailable. Please try again shortly.",
                "session_id": body.session_id,
            },
        )
