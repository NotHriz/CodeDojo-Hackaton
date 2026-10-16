"""Public, rate-limited campus assistant with explicit failure responses."""

from fastapi import APIRouter, HTTPException, Request

from app.schemas import ErrorResponse
from app.services.chat import (
    AIUnavailable, ChatRequest, ChatResponse, DEMO_NOTICE, InvalidAIResponse,
    MAX_ASSISTANT_MESSAGE_CHARS, run_chat,
)

router = APIRouter(prefix="/chat", tags=["assistant"])


@router.post("", response_model=ChatResponse, responses={
    429: {"model": ErrorResponse}, 502: {"model": ErrorResponse},
    503: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
})
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    provider = request.app.state.chat_provider
    repository = request.app.state.place_repository
    if provider is None:
        raise HTTPException(503, "The AI assistant is not configured yet.")
    if repository is None:
        raise HTTPException(503, "Building data is not connected yet.")
    client = request.client.host if request.client else "unknown"
    # Do not trust a caller-supplied forwarding header as a rate-limit identity.
    if not request.app.state.chat_budget.reserve(client):
        raise HTTPException(429, "Assistant request limit reached. Please retry later.", headers={"Retry-After": str(request.app.state.chat_budget.retry_after())})
    try:
        demo_mode = request.app.state.demo_mode
        result = run_chat(body, provider, repository, demo_mode=demo_mode)
        if demo_mode:
            result.data_mode = "demo"
            result.answer = DEMO_NOTICE + result.answer
            if len(result.answer) > MAX_ASSISTANT_MESSAGE_CHARS:
                raise InvalidAIResponse()
        return result
    except AIUnavailable:
        raise HTTPException(503, "The AI assistant is temporarily unavailable. Please retry or use the map and filters.") from None
    except InvalidAIResponse:
        raise HTTPException(502, "The AI assistant returned an unusable response. Please retry or use the map and filters.") from None
