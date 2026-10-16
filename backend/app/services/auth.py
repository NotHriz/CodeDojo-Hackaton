"""Verify Supabase asymmetric access tokens; never trust unsigned claims."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID


class InvalidAccessToken(Exception):
    pass


class AuthenticationUnavailable(Exception):
    pass


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class SupabaseTokenVerifier:
    def __init__(self, project_url: str, *, key_client=None):
        self.issuer = project_url.rstrip("/") + "/auth/v1"
        self.key_client = key_client if key_client is not None else PyJWKClient(
            self.issuer + "/.well-known/jwks.json",
            timeout=5,
            lifespan=300,
            cooldown_duration=30,
        )

    def verify(self, token: str) -> AuthenticatedUser:
        if len(token) > 16384:
            raise InvalidAccessToken()
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in {"ES256", "RS256"} or not header.get("kid"):
                raise InvalidAccessToken()
            # Only the configured project's JWKS is used; jku/x5u headers are ignored.
            key = self.key_client.get_signing_key_from_jwt(token)
            if key.algorithm_name != algorithm:
                raise InvalidAccessToken()
            claims = jwt.decode(
                token,
                key.key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience="authenticated",
                leeway=5,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "role"]},
            )
            if claims["role"] != "authenticated" or claims.get("is_anonymous", False):
                raise InvalidAccessToken()
            return AuthenticatedUser(id=UUID(claims["sub"]))
        except PyJWKClientConnectionError as exc:
            raise AuthenticationUnavailable() from exc
        except (jwt.InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
            raise InvalidAccessToken() from exc
