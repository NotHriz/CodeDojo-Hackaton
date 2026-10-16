# Supabase authentication handoff

Implemented: `GET /api/auth/me`, returning `{"id":"<verified user UUID>"}`. Send a Supabase access token in `Authorization: Bearer <token>`. No email, user metadata, private score, or service credentials are returned.

Supabase Auth owns sign-up, login, refresh, and logout in the frontend. The backend does not accept a claimed user ID in place of authentication. Future contribution routes reuse `app.routers.auth.CurrentUser`.

Configure backend `SUPABASE_URL` to the HTTPS project origin. Use **asymmetric signing keys (ES256 or RS256)** in Supabase; legacy HS256 tokens are intentionally unsupported. Verification uses the configured project's `/auth/v1/.well-known/jwks.json`, not a URL from a token header. PyJWT verifies signature, issuer, `authenticated` audience, expiration, issued-at time, subject UUID, and `authenticated` role. Supabase anonymous sign-in tokens are rejected for contributions even though their role may be authenticated.

Public keys are cached for five minutes, network requests have a five-second timeout, and unknown-key refresh has a cooldown. No network call occurs during application import. Local HTTP Supabase URLs are allowed only outside production.

| Situation | Response |
| --- | --- |
| Missing, malformed, expired, forged, wrong-project, wrong-role token | 401 `unauthorized`, Bearer challenge |
| Project not configured | 503 `service_unavailable` for a bearer-auth request |
| Signing-key service unavailable and no usable cached key | 503 `service_unavailable` |
| Valid access token | 200 with verified user ID |

This validates short-lived JWTs, not immediate server-side revocation, current account bans, or contribution restrictions. Logout/revocation can take until token expiry to be reflected; live restriction checks belong in the forthcoming contributor repository/service. No reviewer/admin privileges are derived from user metadata.

Tests use generated EC/RSA signing keys and local key clients. No real Supabase project or credential has been used. References: [Supabase JWTs](https://supabase.com/docs/guides/auth/jwts), [JWT claims](https://supabase.com/docs/guides/auth/jwt-fields), [PyJWT verification](https://pyjwt.readthedocs.io/en/latest/api.html).
