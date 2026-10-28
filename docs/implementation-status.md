# SwarUtsav implementation status

## Implemented in this branch
- FastAPI REST backend with OpenAPI docs and health checks.
- Registration/login, PBKDF2 password hashing, signed expiring bearer tokens, and server-side user checks.
- Persistent local SQLite tables for users, profiles, questions, interviews, answers, and reports.
- Profile editing, seeded question bank, interview creation/history, answer submission, and report retrieval.
- Responsive React app with authentication, overview dashboard, interview setup/session, profile editor, history, and reports.
- Dockerfiles and Docker Compose for local full-stack startup.

## Explicitly not yet implemented
- Approved external LLM integration. Current feedback uses a transparent baseline heuristic.
- Audio recording upload, Whisper transcription, audio metrics, and camera/video processing.
- Managed production database/object storage, password reset delivery, rate limiting, audit trail, backups, and deployment secrets manager.
- Full admin UI and question-management CRUD.

## Local run
From repository root: `cp .env.example .env`, edit `JWT_SECRET`, then `docker compose up --build`.
Open `http://localhost:3000` and `http://localhost:8000/docs`.

This is a working development foundation, not a claim of production readiness. Run automated tests and perform security review before public deployment.
