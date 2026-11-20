"""Private per-user recordings, explicit authorization and opt-in Whisper transcription."""
from __future__ import annotations
import os
import uuid
import tempfile
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.main import current_user, db, API_PREFIX, now_iso

router = APIRouter(prefix=API_PREFIX, tags=["media"])
STORAGE = Path(os.getenv("RECORDING_PATH", "./data/recordings"))
MAX_RECORDING = 25 * 1024 * 1024
MAX_AUDIO = 12 * 1024 * 1024
MIMES = {"video/webm": ".webm", "video/mp4": ".mp4", "audio/webm": ".webm",
         "audio/wav": ".wav", "audio/mpeg": ".mp3", "audio/mp4": ".m4a"}
# This is a local development storage backend. Use a private object store in production.

def ensure_tables():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS recordings(
          id TEXT PRIMARY KEY, interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          category TEXT NOT NULL, filename TEXT NOT NULL, media_type TEXT NOT NULL,
          file_size INTEGER NOT NULL, created_at TEXT NOT NULL)""")

ensure_tables()

def check_interview(interview_id: int, user_id: int):
    with db() as conn:
        row = conn.execute("SELECT id FROM interviews WHERE id=? AND user_id=?",
                           (interview_id, user_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Interview not found")

async def limited_upload(file: UploadFile, max_bytes: int):
    chunks = []
    total = 0
    while True:
        data = await file.read(1024 * 1024)
        if not data:
            break
        total += len(data)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="Media file is too large")
        chunks.append(data)
    if not total:
        raise HTTPException(status_code=422, detail="Media file is empty")
    return b"".join(chunks)

def sniff_media(data: bytes, content_type: str):
    if content_type not in MIMES:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    # Lightweight signature validation, not a substitute for malware scanning.
    if content_type in ("video/webm", "audio/webm") and not data.startswith(b"\x1a\x45\xdf\xa3"):
        raise HTTPException(status_code=415, detail="Invalid WebM media signature")
    if content_type in ("video/mp4", "audio/mp4") and data[4:8] != b"ftyp":
        raise HTTPException(status_code=415, detail="Invalid MP4 media signature")
    if content_type == "audio/wav" and not (data[:4] == b"RIFF" and data[8:12] == b"WAVE"):
        raise HTTPException(status_code=415, detail="Invalid WAV signature")
    if content_type == "audio/mpeg" and not (data[:3] == b"ID3" or data[:1] == b"\xff"):
        raise HTTPException(status_code=415, detail="Invalid MP3 signature")

@router.post("/interviews/{interview_id}/recordings", status_code=201)
async def upload_recording(interview_id: int, category: str, file: UploadFile = File(...),
                           user=Depends(current_user)):
    check_interview(interview_id, user["id"])
    if category not in {"screen", "camera", "audio"}:
        raise HTTPException(status_code=422, detail="Invalid recording category")
    media_type = (file.content_type or "").split(";")[0].strip().lower()
    if media_type not in MIMES:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    if category == "audio" and not media_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Expected audio upload")
    if category in ("screen", "camera") and not media_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Expected video upload")
    data = await limited_upload(file, MAX_RECORDING)
    sniff_media(data, media_type)
    rid = str(uuid.uuid4())
    folder = STORAGE / str(user["id"])
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / (rid + MIMES[media_type])
    try:
        with open(path, "xb") as f:
            f.write(data)
        os.chmod(path, 0o600)
        with db() as conn:
            conn.execute("""INSERT INTO recordings
            (id,interview_id,user_id,category,filename,media_type,file_size,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (rid, interview_id, user["id"], category, path.name, media_type, len(data), now_iso()))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"id": rid, "category": category, "size": len(data), "status": "stored_private"}

def recording_for_user(rid, user_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM recordings WHERE id=? AND user_id=?", (rid,user_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return row

@router.get("/recordings/{recording_id}")
def download_recording(recording_id: str, user=Depends(current_user)):
    row = recording_for_user(recording_id, user["id"])
    path = STORAGE / str(user["id"]) / row["filename"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Recording missing")
    return FileResponse(path, media_type=row["media_type"],
                        filename=f"swarutsav-{row['category']}{path.suffix}")

@router.delete("/recordings/{recording_id}", status_code=204)
def delete_recording(recording_id: str, user=Depends(current_user)):
    row = recording_for_user(recording_id, user["id"])
    path = STORAGE / str(user["id"]) / row["filename"]
    with db() as conn:
        conn.execute("DELETE FROM recordings WHERE id=? AND user_id=?", (recording_id,user["id"]))
    path.unlink(missing_ok=True)
    return None

@router.get("/interviews/{interview_id}/recordings")
def list_recordings(interview_id: int, user=Depends(current_user)):
    check_interview(interview_id, user["id"])
    with db() as conn:
        rows = conn.execute("""SELECT id,category,media_type,file_size,created_at
             FROM recordings WHERE interview_id=? AND user_id=? ORDER BY created_at DESC""",
             (interview_id,user["id"])).fetchall()
    return [dict(row) for row in rows]

@lru_cache(maxsize=1)
def whisper_model():
    # Optional installation: pip install faster-whisper (includes audio decode via PyAV)
    from faster_whisper import WhisperModel
    model_size = os.getenv("WHISPER_MODEL", "tiny")
    if model_size not in {"tiny", "base", "small", "medium"}:
        raise RuntimeError("Invalid WHISPER_MODEL")
    return WhisperModel(model_size, device="cpu", compute_type="int8")

@router.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...), user=Depends(current_user)):
    media_type = (file.content_type or "").split(";")[0].strip().lower()
    if media_type not in {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4"}:
        raise HTTPException(status_code=415, detail="Upload an audio file")
    data = await limited_upload(file, MAX_AUDIO)
    sniff_media(data, media_type)
    if os.getenv("ENABLE_WHISPER", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Whisper is not enabled on this server")
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=MIMES[media_type], delete=False) as tmp:
            tmp.write(data)
            tmp_name = tmp.name
        model = whisper_model()
        segments, _ = model.transcribe(tmp_name, beam_size=2, vad_filter=True)
        transcript = " ".join(s.text.strip() for s in segments).strip()
        return {"text": transcript[:12000], "engine": "faster_whisper"}
    except (ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Whisper model unavailable") from exc
    finally:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)
