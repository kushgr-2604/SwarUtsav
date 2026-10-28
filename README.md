# SwarUtsav

**SwarUtsav is an AI-assisted interview preparation and behavioural analytics portal** for practising technical, HR and behavioural interviews, submitting answers, and reviewing structured feedback and progress over time. The application uses a React frontend and FastAPI REST API, with Docker support for local development.

## Current implementation
This branch implements persistent local data, candidate registration/login, signed expiring bearer tokens, profile editing, a seeded question bank, interview creation/history, answer submission, baseline feedback, and reports. The scoring logic is explicitly a transparent starter rubric—not an LLM assessment. Speech-to-text, audio/video analysis, an approved external AI provider, object storage, and managed production persistence are future integrations.

## Run with Docker
1. Install Docker Desktop/Engine with Compose.
2. Copy `.env.example` to `.env` and set a long random `JWT_SECRET`.
3. Run `docker compose up --build` at the repository root.
4. Open http://localhost:3000 and API docs at http://localhost:8000/docs.

The local SQLite database is persisted in the `swarutsav-data` Docker volume.

## Run without Docker
Backend: `cd backend`, create a virtual environment, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --port 8000`.
Frontend: in another terminal run `cd frontend && npm install`, then set `REACT_APP_API_URL=http://localhost:8000/api/v1` and run `npm start`.

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/auth/me` | Current user |
| GET/PUT | `/api/v1/profile` | Read/update profile |
| GET | `/api/v1/questions` | Browse questions |
| POST/GET | `/api/v1/interviews` | Create/list sessions |
| POST | `/api/v1/interviews/{id}/answers` | Submit answer |
| POST | `/api/v1/interviews/{id}/complete` | Complete session and create report |
| GET | `/api/v1/reports` | List reports |
| GET | `/api/v1/reports/{id}` | Report details |

## Production hardening
Before public production use, migrate SQLite to managed persistence, rotate secrets, configure HTTPS and environment-specific CORS, add rate limiting, password recovery, audit logs, backups, monitoring and automated integration tests. Integrate an external AI provider only after privacy, cost and institutional requirements are approved. Camera-derived outputs must describe observable behaviour only, not infer emotion, honesty, personality or confidence.
