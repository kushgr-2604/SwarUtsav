# SwarUtsav ZIP integration review

## Existing GitHub `main`
- `frontend/`: minimal JavaScript React starter.
- `backend/`: minimal Python FastAPI app with a health endpoint and test.
- `docs/`: initial architecture/API/database/deployment placeholders.

## Uploaded ZIP
- `ExQt3OIywpNfC44V-grok-workspace/`: TanStack Start + React/TypeScript prototype with routes for registration, login, dashboard, interview setup/session, report, history and admin.
- `src/lib/scoring.ts`: **heuristic** answer scoring and report aggregation; not Llama-based evaluation.
- `migrations/0002_swarutsav.sql`: relational tables and question seed data; not the planned DynamoDB layout.
- Several generator/runtime directories (`.grok/`, `.vercel/`, `.tanstack/`) and screenshots are present and should not be committed to the source tree.

## Compatibility decisions needed before replacing `main`
- Choose React JS + FastAPI vs TanStack Start full-stack TypeScript frontend.
- Choose Postgres-style persistence vs DynamoDB or define an explicit migration boundary.
- Keep authentication/session data isolated, with server-side authorization.
- Keep AI-processing claims separate from currently implemented mock/heuristic functionality.
- Verify camera consent and do not infer emotion, personality, honesty or confidence from facial features.

This branch is an **initial, isolated ZIP integration**. Full-source migration is deferred until compatibility and security checks are complete.
