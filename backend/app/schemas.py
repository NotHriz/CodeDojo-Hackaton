"""Public foundation schemas; building/report/AI contracts remain to be agreed."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["akses-campus-api"] = "akses-campus-api"


class APIError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: APIError
