"""Reusable sign-in dependency and minimal public identity endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from app.schemas import ErrorResponse

from app.services.auth import (
    AuthenticatedUser,
    AuthenticationUnavailable,
    InvalidAccessToken,
)

bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["authentication"], responses={
    401: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
})


def require_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(401, "Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    verifier = request.app.state.token_verifier
    if verifier is None:
        raise HTTPException(503, "Authentication is not configured yet.")
    try:
        return verifier.verify(credentials.credentials)
    except InvalidAccessToken:
        raise HTTPException(
            401, "Your session is invalid or expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AuthenticationUnavailable:
        raise HTTPException(503, "Authentication is temporarily unavailable.") from None


CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]


class IdentityResponse(BaseModel):
    id: UUID


@router.get("/me", response_model=IdentityResponse)
def me(user: CurrentUser) -> IdentityResponse:
    return IdentityResponse(id=user.id)
