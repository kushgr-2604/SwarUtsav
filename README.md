# SwarUtsav

SwarUtsav is an interview-practice portal for students and job seekers. Candidates choose a target role and interview type, answer technical, HR, or behavioural questions, and review a report with per-answer feedback and relevance, completeness, and clarity scores.

## First end-to-end feature: text-answer scoring
A candidate can register, start a practice session, receive questions, submit text answers, complete the interview, and retrieve a persisted report. The current scorer is a **deterministic baseline heuristic, not ML**: it uses rough keyword overlap and answer length to estimate relevance, completeness, and clarity. The planned ML component is semantic answer scoring and feedback against an explicit rubric through an approved model provider. Speech pace/filler-word analysis is a separate future feature and is not implemented yet.

## Current implementation
- FastAPI REST API and interactive docs.
- Candidate registration/login with PBKDF2 password hashing and signed expiring bearer tokens.
- Profile editing, seeded question bank, interview creation/history, answer submission, baseline feedback, and report retrieval.
- React UI for authentication, dashboard, practice session, history, reports, and profile.
- Docker Compose setup, backend/frontend Dockerfiles, Nginx SPA routing, and API tests for the core flow.

## Run with Docker
1. Install Docker Desktop/Engine with Compose.
2. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a strong random secret.
3. Run `docker compose up --build` from the repository root.
4. Open http://localhost:3000 and API docs at http://localhost:8000/docs.

The local SQLite database is persisted in the `swarutsav-data` Docker volume.

## Run without Docker
Backend: `cd backend`, create a virtual environment, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --port 8000`.
Frontend: in another terminal run `cd frontend && npm install`, set `REACT_APP_API_URL=http://localhost:8000/api/v1`, then `npm start`.

## API overview
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/v1/auth/register` | Register candidate |
| POST | `/api/v1/auth/login` | Login |
| GET/PUT | `/api/v1/profile` | Read/update profile |
| GET | `/api/v1/questions` | Browse question bank |
| POST/GET | `/api/v1/interviews` | Create/list sessions |
| POST | `/api/v1/interviews/{id}/answers` | Submit answer and score |
| POST | `/api/v1/interviews/{id}/complete` | Complete session |
| GET | `/api/v1/reports` | List reports |
| GET | `/api/v1/reports/{id}` | Read report |

## Production hardening
The scoring is not an ML model and is only for development/practice. Before public production use, run automated tests and container builds; migrate SQLite to managed persistence; rotate secrets; configure HTTPS, rate limiting, password recovery, audit logs, backups, and monitoring. Integrate an external model only after privacy, cost, and institutional approval. Do not infer emotion, honesty, personality, or confidence from video.
