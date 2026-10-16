"""FastAPI composition root, including opt-in configured PostgreSQL browsing."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.config import Settings
from app.database import Database
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.community import router as community_router
from app.routers.health import router as health_router
from app.routers.places import router as places_router
from app.schemas import ErrorResponse
from app.services.places import PlaceRepository
from app.services.auth import SupabaseTokenVerifier, TokenVerifier
from app.services.chat import ChatBudget, ChatProvider, DeepSeekProvider
from app.services.community import CommunityRepository, TrustPolicy
from app.services.demo_places import DemoPlaceRepository
from app.services.postgres_places import PostgresPlaceRepository

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str, headers=None) -> JSONResponse:
    body = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status, content=body.model_dump(), headers=headers)


def create_app(
    settings: Settings | None = None,
    *,
    place_repository: PlaceRepository | None = None,
    token_verifier: TokenVerifier | None = None,
    chat_provider: ChatProvider | None = None,
    chat_budget: ChatBudget | None = None,
    community_repository: CommunityRepository | None = None,
    trust_policy: TrustPolicy | None = None,
    contribution_budget: ChatBudget | None = None,
) -> FastAPI:
    """Build the API without opening database connections or contacting providers."""
    settings = settings if settings is not None else Settings()
    # Explicit real adapters always take precedence; failures never trigger demo data.
    effective_places = place_repository
    database = None
    if effective_places is None and settings.database_url.get_secret_value():
        database = Database(settings.database_url.get_secret_value())
        effective_places = PostgresPlaceRepository(database)
    if effective_places is None and settings.demo_data_enabled:
        effective_places = DemoPlaceRepository()
    demo_mode = isinstance(effective_places, DemoPlaceRepository)
    if demo_mode and settings.app_env == "production":
        raise ValueError("Demo building data is not allowed in production.")
    if demo_mode and community_repository is not None:
        raise ValueError("Local demo buildings cannot be combined with a community persistence adapter.")

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            if database is not None:
                database.close()

    api = FastAPI(
        title="Akses Campus API",
        version="0.1.0",
        description=(
            "LOCAL DEMO: fictional building records, not verified IIUM facilities. Real AI requests still use DeepSeek credit."
            if demo_mode else "IIUM Gombak accessibility API. PostgreSQL browsing is enabled when DATABASE_URL is configured."
        ),
        debug=False,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    api.state.settings = settings
    api.state.place_repository = effective_places
    api.state.demo_mode = demo_mode
    api.state.community_repository = community_repository
    api.state.trust_policy = trust_policy
    api.state.contribution_budget = contribution_budget if contribution_budget is not None else ChatBudget(
        per_minute=5, per_day=500
    )
    api.state.token_verifier = token_verifier if token_verifier is not None else (
        SupabaseTokenVerifier(settings.supabase_url) if settings.supabase_url else None
    )
    api.state.chat_provider = chat_provider if chat_provider is not None else (
        DeepSeekProvider(settings) if settings.ai_api_key.get_secret_value() else None
    )
    api.state.chat_budget = chat_budget if chat_budget is not None else ChatBudget(
        per_minute=settings.chat_requests_per_minute, per_day=settings.chat_requests_per_day
    )

    @api.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed", 409: "conflict", 422: "validation_error", 429: "rate_limited", 502: "upstream_error", 503: "service_unavailable"}.get(
            exc.status_code, "request_failed"
        )
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error_response(exc.status_code, code, message, exc.headers)

    @api.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        # Do not echo request bodies or invalid values, which may contain credentials.
        return error_response(422, "validation_error", "Request validation failed.")

    @api.middleware("http")
    async def handle_unexpected_error(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # Avoid logging provider error messages or request values with secrets.
            logger.error("Unhandled backend exception: %s", type(exc).__name__)
            return error_response(
                500, "internal_error", "The server could not complete the request."
            )

    # Added last so CORS also wraps the sanitized unexpected-error response.
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=["Retry-After"],
    )
    api.include_router(health_router, prefix="/api")
    api.include_router(places_router, prefix="/api")
    api.include_router(auth_router, prefix="/api")
    api.include_router(chat_router, prefix="/api")
    api.include_router(community_router, prefix="/api")
    return api


app = create_app()
