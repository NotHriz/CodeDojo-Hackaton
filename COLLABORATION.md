# Working together without conflicting changes

Use separate local clones and short feature branches. Each area has one writer at a time. File ownership prevents most textual conflicts; agreed API/data contracts prevent code that merges cleanly but does not work together.

These rules are a team agreement and instructions for agents, not operating-system file locks or GitHub-enforced restrictions. Read [AGENTS.md](AGENTS.md) when working with an agent and [onboarding.md](onboarding.md) for project scope.

## Ownership

Specific file exceptions override directory ownership.

| Area | Primary writer | Other teammates do |
| --- | --- | --- |
| `frontend/**`, including its dependencies and lockfile | Teammate 1: frontend | Read, review, or propose API requirements |
| `backend/**`, except the two database-owned files below | User: backend | Read, review, or request a backend change |
| `backend/app/models.py` | Teammate 3: database | Agree required fields before the database owner edits |
| `backend/app/database.py` | Teammate 3: database | Agree session interface before backend services use it |
| `supabase/**`, `seed/**` | Teammate 3: database | Submit campus observations to the database owner |
| `contracts/**` | User: contract editor, with affected teammate review | Agree changes before implementation; do not edit competing versions |
| Root `README.md`, `onboarding.md`, `AGENTS.md`, this guide, `.gitignore`, and future root CI/deployment configuration | User: integration owner | Send requested edits or arrange a scoped handoff |

Teammate 3 owns database schema/migrations, not API response shapes. The backend owner controls `schemas.py`. The database owner may add necessary Python database dependencies through an agreed handoff to the backend owner; do not edit the same dependency manifest concurrently.

Owners may explicitly delegate a named file/task to another person or agent. Record the scope in the task/PR, and return ownership when the task finishes. Reading other areas is encouraged. Do not copy backend or database internals into frontend code to avoid coordination.

## Branch workflow

Keep `main` as the integrated demo baseline. Start each task from the latest `main`, then create a branch:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/frontend-map
```

Run this with a clean working tree. If you have changes, commit them on their current task branch or deliberately stash them first; never reset someone else's work to make a command succeed.

Example branch names:

- `feat/frontend-map`
- `feat/backend-chat`
- `feat/database-buildings`

Commit only your task's files using explicit paths:

```powershell
git add -- frontend/src/components frontend/src/views
git diff --cached
git commit -m "feat: add building selection UI"
git push -u origin feat/frontend-map
```

These paths are examples; include only the files actually changed for the task. Open a small pull request to `main`. State the behavior, checks run, contract changes, migrations, and any handoff needed. Do not claim placeholder modules are working features.

The integration owner merges PRs one at a time after review and appropriate checks. Use one agreed merge method; squash merging is a reasonable default for these short task branches. Only the integration owner performs routine merges or direct integration fixes on `main`.

Before integration, bring current `main` into your feature branch:

```powershell
git fetch origin
git merge origin/main
```

Resolve conflicts on the feature branch with the affected owner, run relevant checks, and push again. Avoid rebasing published/shared branches or force-pushing. Delete completed task branches when convenient and start the next task from current `main`.

## API and database contracts come first

Before separate frontend/backend/database implementation, agree a small vertical slice: building list -> details -> authenticated report -> votes -> derived status.

Record interface decisions in `contracts/`. The backend owner is the single editor; frontend/database teammates review affected interfaces.

For each endpoint agree:

- Method/path and authentication requirement.
- Query parameters, request fields, and example JSON responses.
- ID types, nullable fields, date/time format, and enum values.
- Error shape and HTTP status behavior, including AI outages.
- Filter meaning: required facilities match `yes`; unknown stays unknown.
- Warning behavior: matching buildings remain visible with active warnings.
- Chat result shape for source cards, interpreted filters, and map/list updates.

Database and API enums must be mapped deliberately, not guessed independently. Do not introduce `confirmed` in one layer while another expects `community_corroborated`. Keep private reliability out of public API shapes.

Frontend mocks are allowed for development after the contract is agreed. Label mock mode explicitly; never silently return mocks when a real API call fails. Remove or disable mock mode for the live product demo unless clearly identified as a mock demonstration.

## Shared database rules

- The database owner applies migrations to the shared Supabase project. Others request changes instead of editing tables manually in the dashboard.
- Keep schema changes, policies, and migration scripts versioned in `supabase/` once tooling is selected.
- Never rewrite a migration already applied to the shared database. Add a new forward migration.
- Coordinate migration order with backend code; prefer additive changes until all consumers migrate.
- Seed imports must be repeatable and must not erase existing reports or votes.
- Announce schema-changing work, seed/reset operations, and Auth/Storage configuration changes in the team's normal channel. Do not reset shared data without agreement from affected teammates.
- Use local environment files for credentials. Never commit secrets or private contributor scores as seed data.

## Task handoff template

Put this in the task description or PR; a shared continuously edited task file is unnecessary.

```text
Owner/role:
Branch:
Goal:
Files I will edit:
Contracts/dependencies:
Acceptance check:
Cross-area handoff, if any:
```

Check in when an interface changes, when you are blocked on another area, and when a slice is ready to integrate. Keep PRs small enough to review and test during the hackathon. Integrate early rather than leaving three disconnected applications until the last hour.

## If a conflict occurs

1. Check `git status` and inspect both changes.
2. Contact the file owner and decide the intended combined behavior.
3. Resolve just the affected files. Do not select “ours” or “theirs” across the whole repository.
4. Run the affected checks and the shared user journey, then commit the resolution.

If a merge becomes confusing, `git merge --abort` can return to the pre-merge state. Do not use `git reset --hard`, broad checkout/discard operations, or force pushes as routine conflict fixes.

## Optional GitHub enforcement

This change does not configure repository settings. If available for the repository, a `main` ruleset/branch protection requiring pull requests and preventing force pushes can enforce the integration workflow. CODEOWNERS can request reviews but does not lock files; real GitHub usernames are needed before adding it. Ownership documentation alone cannot prevent direct pushes.
