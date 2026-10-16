# Agent collaboration instructions

Read `onboarding.md`, `README.md`, and `COLLABORATION.md` before implementing. Preserve the agreed Vue/Tailwind, FastAPI, Supabase, DeepSeek, Netlify, and Render architecture and the community-verification design.

## Select a scope before editing

Use the role explicitly assigned in the task. If none is assigned, infer it from the requested work. For broad implementation with no clear owner, inspect and plan first, then clarify the role before changing multiple ownership areas. Documentation tasks belong to the integration owner by default. An explicit user-authorized cross-area task is a scoped handoff; do not ask for the same authorization again.

| Role | Writable scope for its task |
| --- | --- |
| Frontend | `frontend/**` |
| Backend | `backend/**` except `backend/app/models.py` and `backend/app/database.py` |
| Database | `supabase/**`, `seed/**`, `backend/app/models.py`, `backend/app/database.py` |
| Integration | Root documentation/configuration and `contracts/**`; cross-area implementation only when assigned |

Read any area to understand dependencies. When a fix needs another owner's files, describe the concrete needed change and request a scoped handoff; continue independent work within scope. Do not silently rewrite other areas, dependency manifests, generated lockfiles, or shared contracts.

The database owner also maintains root [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md), an explicit user-authorized documentation handoff. Read it before database work and update it in each database task/PR that changes schema, models/sessions, adapters, seeds, policies, verification, or deployment readiness. Distinguish pending PRs, merged code, local tests, and shared deployment; include remaining backend dependencies. This standing scope covers that handoff file only, alongside the database paths above.

## Worktree and Git discipline

- Inspect Git status before editing. Preserve existing user/teammate changes; never discard or overwrite them to obtain a clean workspace.
- Work on a task branch for implementation. Use separate clones/worktrees for concurrently running developers or agents; different branches in one working directory do not isolate work.
- Do not switch the branch of a shared working directory while another worker is using it.
- Stage explicit task paths, review the staged diff, and exclude unrelated work and credentials.
- Commit/push only when requested or authorized for the task. Do not force-push or perform destructive resets as a normal integration step.
- Do not merge to `main` unless assigned integration work. Resolve conflicts with the affected owner rather than choosing one entire side blindly.

## Contracts and verification

- Follow `contracts/` when implemented contracts exist. `contracts/places.md` describes the tested building API proposal and persistence handoff; teammate review and the real adapter remain pending. Other interfaces still need agreement.
- Do not guess shared field names, enum values, identity/session interfaces, or community trust thresholds independently across layers.
- Report cross-area dependencies and changed interfaces in the task/PR handoff. Keep tests within the relevant area unless a cross-area change is assigned.
- Run checks appropriate to the change; report what actually ran. The backend foundation is runnable with pinned dependencies and tests; see `backend/README.md`. Frontend and database modules are still pending implementation.
- Keep documentation accurate about placeholders versus implemented functionality.
- Public browsing is allowed; reporting/voting requires authenticated identity. Private reliability and backend secrets must never leak into public responses or frontend bundles.
- Never substitute fake data or canned accessibility answers for an AI/API failure in the live application.
- The user-authorized local demo is an explicit development-only fixture mode, not an outage fallback. Preserve its default-off flag, production rejection, real-adapter precedence, and visible fictional-data labels.

Do not spawn sub-agents unless the user or another applicable instruction explicitly requests delegation or parallel agent work. These boundaries coordinate work; they are not filesystem or GitHub access controls.
