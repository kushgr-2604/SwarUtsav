# SwarUtsav — product and ML scope

## What the portal does
SwarUtsav is an interview-practice portal for students and job seekers. Candidates choose a target role and interview type, answer technical/HR/behavioural questions, and review a report with per-answer feedback and relevance, completeness, and clarity scores.

## Core vertical slice: text-answer scoring
The first end-to-end feature is text-based mock interview scoring:
1. Candidate registers and receives an access token.
2. Candidate starts a session and receives questions from the seeded question bank.
3. Candidate submits a text answer to each question.
4. The backend computes rubric-based relevance, completeness, and clarity scores and persists the response.
5. Candidate completes the session and retrieves a persisted report.

The current scoring is a **deterministic baseline heuristic, not machine learning**. It uses answer length and keyword overlap as rough signals and returns simple improvement prompts. This establishes the complete product workflow before a model is introduced; the numbers should be treated as practice guidance, not objective measures of candidate quality.

## ML boundary and next step
The planned ML component is semantic scoring and feedback for a candidate's answer against the question and an explicit rubric, using an approved external language model or a validated locally hosted model if institutionally permitted. The provider must be configured server-side, protected by environment secrets, and tested with representative answers and rubric examples. Keep the baseline as a fallback and label which evaluator produced every score. Speech pace and filler-word analysis would be a separate future feature requiring audio capture/transcription and should not be claimed as implemented.

## Implemented in this branch
- FastAPI endpoints and OpenAPI docs.
- Candidate registration/login with PBKDF2 password hashing and signed expiring bearer tokens.
- Profile persistence and seeded question bank.
- Interview creation/history, answer submission, baseline scoring, completion, and report retrieval.
- React screens for authentication, overview, setup/practice, history, reports, and profile.
- Dockerfiles, Docker Compose, Nginx SPA routing, health check, and API tests including the candidate-to-report flow.

## Verification status
End-to-end API tests are committed in this branch but must still be run in CI or a local environment. Do not describe the branch as production-ready until the frontend build, API tests, container build, and security review pass.

## Run locally
From repository root, set a unique `JWT_SECRET` in `.env`, then run `docker compose up --build`. UI: `http://localhost:3000`; API docs: `http://localhost:8000/docs`.
