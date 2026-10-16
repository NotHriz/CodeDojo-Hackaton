"""Real signatures with local generated keys; no Supabase network requests."""

import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient
from jwt import PyJWK
from jwt.exceptions import PyJWKClientConnectionError

from app.config import Settings
from app.main import create_app
from app.services.auth import InvalidAccessToken, SupabaseTokenVerifier

ISSUER = "https://example.supabase.co/auth/v1"


@pytest.fixture
def signing():
    private = ec.generate_private_key(ec.SECP256R1())
    public = jwt.algorithms.ECAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update(kid="test-key", alg="ES256", use="sig")

    class LocalKeyClient:
        def get_signing_key_from_jwt(self, token):
            return PyJWK.from_dict(public)

    return private, SupabaseTokenVerifier("https://example.supabase.co", key_client=LocalKeyClient())


def claims(**updates):
    now = int(time.time())
    return {
        "iss": ISSUER, "aud": "authenticated", "sub": str(uuid4()),
        "iat": now, "exp": now + 300, "role": "authenticated", **updates,
    }


def signed(private, payload):
    return jwt.encode(payload, private, algorithm="ES256", headers={"kid": "test-key"})


def test_verified_identity_does_not_expose_claims_or_reputation(signing):
    private, verifier = signing
    payload = claims(email="private@example.com", user_metadata={"score": 100, "admin": True})
    with TestClient(create_app(Settings(_env_file=None), token_verifier=verifier)) as client:
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer " + signed(private, payload)})
        assert response.status_code == 200
        assert response.json() == {"id": payload["sub"]}


@pytest.mark.parametrize("updates", [
    {"exp": 1}, {"iat": int(time.time()) + 600}, {"iss": "https://attacker.example/auth/v1"},
    {"aud": "anon"}, {"role": "service_role"}, {"is_anonymous": True}, {"sub": "not-a-user-id"},
])
def test_invalid_claims_are_rejected(signing, updates):
    private, verifier = signing
    with pytest.raises(InvalidAccessToken):
        verifier.verify(signed(private, claims(**updates)))


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "iss", "aud", "role"])
def test_required_claims(signing, missing):
    private, verifier = signing
    payload = claims()
    del payload[missing]
    with pytest.raises(InvalidAccessToken):
        verifier.verify(signed(private, payload))


def test_forged_and_unsigned_tokens_are_rejected(signing):
    private, verifier = signing
    wrong_key = ec.generate_private_key(ec.SECP256R1())
    for token in (
        signed(wrong_key, claims()),
        jwt.encode(claims(), "attacker-controlled-key-that-is-long-enough", algorithm="HS256", headers={"kid": "test-key"}),
        jwt.encode(claims(), "", algorithm="none"),
        "malformed",
        "x" * 16385,
    ):
        with pytest.raises(InvalidAccessToken):
            verifier.verify(token)


def test_rsa_keys_are_supported():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update(kid="rsa", alg="RS256")

    class Keys:
        def get_signing_key_from_jwt(self, token):
            return PyJWK.from_dict(public)

    verifier = SupabaseTokenVerifier("https://example.supabase.co", key_client=Keys())
    payload = claims()
    token = jwt.encode(payload, private, algorithm="RS256", headers={"kid": "rsa"})
    assert str(verifier.verify(token).id) == payload["sub"]


def test_missing_invalid_and_unconfigured_auth(signing):
    private, verifier = signing
    with TestClient(create_app(Settings(_env_file=None, supabase_url=""))) as client:
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer token"}).status_code == 503
    with TestClient(create_app(Settings(_env_file=None), token_verifier=verifier)) as client:
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["error"]["code"] == "unauthorized"


def test_key_service_outage_is_503_not_success(signing):
    private, _ = signing

    class OfflineKeys:
        def get_signing_key_from_jwt(self, token):
            raise PyJWKClientConnectionError("private provider diagnostic")

    verifier = SupabaseTokenVerifier("https://example.supabase.co", key_client=OfflineKeys())
    with TestClient(create_app(token_verifier=verifier)) as client:
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer " + signed(private, claims())})
        assert response.status_code == 503
        assert "private provider diagnostic" not in response.text


def test_public_health_stays_public():
    with TestClient(create_app(Settings(_env_file=None, supabase_url=""))) as client:
        assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("url", ["http://remote.example", "https://user:pass@example.com", "https://example.com/path", "https://example.com?key=secret"])
def test_auth_project_origin_validation(url):
    with pytest.raises(ValueError):
        Settings(_env_file=None, supabase_url=url)


def test_production_auth_rejects_local_http():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production", supabase_url="http://localhost:54321")
