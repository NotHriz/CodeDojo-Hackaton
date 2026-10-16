# Campus assistant API — backend handoff v0.1

Implemented `POST /api/chat`. Public browsing/chat does not require sign-in. Requires backend `AI_API_KEY` plus an injected building repository; neither is provisioned by this PR. Frontend/database review and a real-provider smoke test remain pending.

```json
{
  "message": "Find a study building with a step-free entrance",
  "history": [],
  "selected_place_id": null
}
```

Limits: message 1–1000 characters after trimming, up to six history messages of 1–1000 characters each with only `user`/`assistant` roles, optional selected building ID up to 128 characters. Unknown request fields are rejected. History is context, not authoritative evidence; do not send medical data, location traces, or unrelated chat.

The response contains `answer`, `status` (`answered`, `clarification`, `no_matches`), `places` (building summaries), `sources` (cited building details), `applied_filters` (nullable), and `total_matches` (nullable). Place DTOs follow [places.md](places.md). Frontend must render warning/source cards and editable filters from these structured records, not parse the answer for markers or verification.

AI can call only `search_places` and `get_place_details`. Arguments are validated with extra fields forbidden. Campus is pinned to IIUM Gombak. At most three tool calls, at most one search, at most five building records, and at most two model requests occur per user request. The second model request cannot run more tools. There are no write, voting, arbitrary SQL, URL-fetching, or web-search tools.

Final citations must refer to actual records returned during the current request. Unknowns, active warnings, and dated observations remain in source cards. No-match responses come from actual query results and ask which requirement to change; requirements are never silently relaxed. Source-card fields are database-backed; free-form model wording is not independently semantically verified and must not be treated as certification. A real-provider/user evaluation is still needed.

Retrieved reports, descriptions, and conversation history are treated as untrusted data in the prompt. Tool permissions and argument validation are enforced outside the model. Prompt injection is not claimed to be solved; it cannot grant a tool access to writes, credentials, other campuses, or unsupported actions.

| Failure | Response |
| --- | --- |
| Invalid input | 422 `validation_error` |
| Process request budget exceeded | 429 `rate_limited` with `Retry-After` |
| Unsupported tool, invalid arguments/citations, malformed/truncated model response | 502 `upstream_error` |
| Missing AI configuration or building adapter | 503 `service_unavailable` |
| Provider timeout, authentication/billing/rate/network failure | 503 `service_unavailable` |
| Unexpected persistence failure | Sanitized 500 `internal_error` |

Error responses have no `answer`, sources, or fake success data. Show an explicit system error and retry; map/list filters remain independent. No canned accessibility answer replaces an AI outage.

DeepSeek uses a fixed HTTPS endpoint, `deepseek-flash`, thinking disabled, 600 output tokens per call by default, and a 15-second per-call timeout. Configure `AI_MAX_OUTPUT_TOKENS` (100–1200) and `AI_TIMEOUT_SECONDS` (1–30). No paid calls were made during implementation. Only numerical token counts are logged when supplied; raw chat and evidence are not logged/stored by this service. DeepSeek still receives the bounded context needed to answer.

Demo request limits default to five attempts per client address per minute and 100 globally per UTC day. Failed provider attempts count. Limits are in-memory per process and reset on restart; they are **not** a dollar cap or production/distributed abuse prevention. Shared networks/proxies may share a client bucket. Caller-provided forwarding headers are not directly used to override identity. Configure an edge/distributed limiter before broader public exposure.

Tests use scripted providers and HTTPX mock transports, including forged citations, unsupported tools, provider failures, no-match behavior, rate limits, and preservation of warnings. Real Supabase data, DeepSeek quality, and frontend interaction are not yet validated. References: [DeepSeek tool calling](https://api-docs.deepseek.com/guides/tool_calls/), [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/).
