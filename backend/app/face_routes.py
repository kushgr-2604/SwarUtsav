"""Optional, opt-in face presence and one-time face verification.

No face photos or embeddings are persisted. Face matching is not proof of identity,
and candidates must have a non-biometric alternative.
"""
from __future__ import annotations
import io
import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.main import API_PREFIX, current_user

router = APIRouter(prefix=API_PREFIX + "/face", tags=["face"])
MAX_IMAGE_BYTES = 3 * 1024 * 1024

async def read_image(upload: UploadFile):
    if upload.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=415, detail="JPEG or PNG required")
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be under 3 MB")
    if upload.content_type == "image/jpeg" and not data.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=415, detail="Invalid JPEG")
    if upload.content_type == "image/png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail="Invalid PNG")
    return data

def get_cv():
    try:
        import cv2
        import numpy
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Face processing packages not installed") from exc
    return cv2, numpy, Image

def cv_image(data):
    cv2, np, Image = get_cv()
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 5_000_000:
                raise HTTPException(status_code=413, detail="Image dimensions too large")
            image = image.convert("RGB")
            return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Image could not be decoded") from exc

def face_boxes(data):
    cv2, np, _ = get_cv()
    image = cv_image(data)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise HTTPException(status_code=503, detail="Face detection model unavailable")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(45, 45))
    return [{"x": int(x), "y": int(y), "width": int(w), "height": int(h)} for x,y,w,h in faces]

@router.post("/detect")
async def detect_face(image: UploadFile = File(...), user=Depends(current_user)):
    data = await read_image(image)
    boxes = face_boxes(data)
    return {"face_detected": len(boxes) > 0, "face_count": len(boxes),
            "faces": boxes, "method": "opencv_haar_face_detection",
            "note": "Face presence only; does not identify the candidate."}

@router.post("/verify")
async def verify_face(
    enrollment: UploadFile = File(...),
    live: UploadFile = File(...),
    consent: bool = Form(False),
    user=Depends(current_user),
):
    if not consent:
        raise HTTPException(status_code=400, detail="Explicit consent is required")
    enrollment_data = await read_image(enrollment)
    live_data = await read_image(live)
    try:
        import face_recognition
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Optional face verification package is not installed") from exc

    def rgb(data):
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 5_000_000:
                raise HTTPException(status_code=413, detail="Image dimensions too large")
            return np.array(image.convert("RGB"))

    known = face_recognition.face_encodings(rgb(enrollment_data))
    current = face_recognition.face_encodings(rgb(live_data))
    if len(known) != 1 or len(current) != 1:
        return {"status": "uncertain", "matched": None,
                "note": "Exactly one face in each image is required."}
    distance = float(face_recognition.face_distance([known[0]],current[0])[0])
    # Tunable threshold is an implementation baseline, not validated for the population.
    threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.5"))
    if threshold < 0.3 or threshold > 0.65:
        raise HTTPException(status_code=500, detail="Invalid face threshold configuration")
    return {"status": "possible_match" if distance <= threshold else "not_matched",
            "matched": distance <= threshold, "distance": round(distance, 4),
            "method": "face_embedding_comparison",
            "note": "Not a proof of identity or liveness. No biometric template is saved. Manual verification remains available."}
