# SwarUtsav – Student Development Portal + AI Interview Studio

This is an original student-development-and-placement-readiness experience inspired by the **type of services** campus SDC portals provide. It is not an official GLA University website, and no institutional branding or private GLA assets are used.

## Features in this branch

- Responsive student dashboard, practice history, analytics navigation, placement-readiness resource cards, role/difficulty/question-count interview setup.
- Optional **Grok** question generation and answer feedback through a server-side xAI API key; falls back to the curated question bank and transparent baseline rubric when unavailable.
- Optional contextual AI follow-up endpoint. The UI reads a returned follow-up out loud via browser TTS. The follow-up is a practice aid, not part of the persisted/scored question sequence.
- Browser speech synthesis and dictation where supported, plus explicit microphone recording for **faster-whisper** STT.
- Consent-based camera preview, screen and camera recording using `MediaRecorder`; files are local until a user clicks **Upload privately**.
- Authenticated, interview-owner-scoped local recording store with file size/content-type/signature checks, list/download/delete APIs.
- Opt-in OpenCV face presence detection; optional one-time face-image comparison. Verification only indicates similarity, **not identity or liveness**. No face embeddings are stored.

## Setup

```bash
cp .env.example .env
# Set a random JWT_SECRET >=32 characters and optionally XAI_API_KEY.
docker compose up --build
```

Frontend: http://localhost:3000. API documentation: http://localhost:8000/docs.

To configure Grok (optional), add `XAI_API_KEY` in the server-side `.env`. Do not put API secrets into `REACT_APP_*` variables. Set `GROK_MODEL` to an available model supported by your xAI account. Grok requests use `https://api.x.ai/v1/chat/completions` with a 20-second timeout. AI responses are validated before use; the app falls back if a model/key/network request fails.

Whisper: The backend installs neither model weights nor `faster-whisper` by default. For a local Python environment:

```bash
cd backend
pip install -r requirements.txt
pip install faster-whisper
export ENABLE_WHISPER=true
export WHISPER_MODEL=tiny
```

You must enable Whisper and install `faster-whisper` **inside the running backend environment**. Setting the variable in Docker without installing the dependency is insufficient. Model files may download during first load; network, CPU and storage requirements apply. Voice dictation via browser speech recognition is a separate fallback and is not Whisper.

Face presence: OpenCV Haar cascade is installed with the backend requirements. For experimental **one-time face comparison**, you must separately install the `face_recognition` package and its platform-specific native dependencies. Otherwise `POST /api/v1/face/verify` returns 503. Do not use experimental results for adverse decisions; offer manual verification instead. There is no liveness/anti-spoofing detection. Endpoints neither store biometrics nor perform ongoing background surveillance. Protect camera permissions with HTTPS outside localhost.

## API endpoints (authenticated Bearer JWT)

- `POST /api/v1/interviews` — create interview, persist configured question count.
- `POST /api/v1/interviews/{id}/answers` — validate sequential assigned question then evaluate.
- `POST /api/v1/interviews/{id}/followup` — suggest a contextual spoken follow-up; returned question is not counted as an interview answer.
- `POST /api/v1/voice/transcribe` — optional Whisper audio transcription (audio upload).
- `POST /api/v1/face/detect` — face presence from one uploaded JPEG/PNG.
- `POST /api/v1/face/verify` — one-time consent-based face comparison; experimental and optional.
- `POST /api/v1/interviews/{id}/recordings?category=screen|camera|audio` — private recording upload.
- `GET /api/v1/interviews/{id}/recordings` — list own session recordings.
- `GET /api/v1/recordings/{recording_id}` — download own recording.
- `DELETE /api/v1/recordings/{recording_id}` — delete own recording.

## Security & production limitations

Development file storage is local, private by permission and owner-scoped, **not hardened production storage**. Before AWS deployment, replace it with private encrypted S3 with short-lived signed access, antivirus/media scanning, quotas, lifecycle deletion, secure backups, and audit records. The frontend currently stores bearer tokens in browser localStorage; use a more defensible session and refresh design before public deployment. Add rate limiting, stronger secret management, brute-force protection, CSRF/session design, DB migrations, and protected administrative workflows.

Browser speech recognition and display-media audio support vary by browser. Safari and Firefox may not support the same APIs as Chromium. HTTPS/localhost is mandatory for most capture APIs. Screen capture must always be initiated by the user. A face-detection result is not an emotion, confidence, honesty, identity, or hiring-readiness prediction.

## Tests

```bash
cd backend
pytest -q
cd ../frontend
npm ci
npm run build
```

Run manual camera, screen-share, spoken interview, recording permission, API-key-unavailable, and disabled-Whisper tests in a real browser. Recording/face tests intentionally avoid downloading face recognition models. Automated tests and build results must be checked in CI; work in a branch is not evidence that the app is production ready.
