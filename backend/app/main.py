"""FastAPI application entry point; external integrations are not connected yet."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.config import Settings
from app.routers.health import router as health_router
from app.schemas import ErrorResponse

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, message: str, headers=None) -> JSONResponse:
    body = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status, content=body.model_dump(), headers=headers)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API without opening database connections or contacting providers."""
    settings = settings if settings is not None else Settings()
    api = FastAPI(
        title="Akses Campus API",
        version="0.1.0",
        description="IIUM Gombak accessibility API. Only liveness is implemented.",
        debug=False,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    api.state.settings = settings

    @api.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(
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
        allow_headers=["Authorization", "Content-Type"],
    )
    api.include_router(health_router, prefix="/api")
    return api


app = create_app()
