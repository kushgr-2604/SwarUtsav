"""Media authorization and validation regression tests."""
import io
import uuid
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def headers():
    email="media-"+uuid.uuid4().hex[:14]+"@example.org"
    r=client.post("/api/v1/auth/register",json={"name":"Media Tester","email":email,"password":"TestPass-12345678"})
    assert r.status_code==201,r.text
    return {"Authorization":"Bearer "+r.json()["access_token"]}

def interview(auth):
    r=client.post("/api/v1/interviews",headers=auth,json={"target_role":"Software Developer","question_count":3})
    assert r.status_code==201,r.text
    return r.json()["id"]

def test_transcription_requires_authentication():
    r=client.post("/api/v1/voice/transcribe",files={"file":("audio.webm",b"\x1a\x45\xdf\xa3"+b"0"*20,"audio/webm")})
    assert r.status_code==401

def test_upload_rejects_spoofed_media_signature():
    auth=headers()
    iid=interview(auth)
    r=client.post(f"/api/v1/interviews/{iid}/recordings?category=screen",headers=auth,
                  files={"file":("screen.webm",b"not-webm","video/webm")})
    assert r.status_code==415

def test_recording_owner_checks_and_deletion():
    owner=headers()
    other=headers()
    iid=interview(owner)
    payload=b"\x1a\x45\xdf\xa3"+b"0"*32
    r=client.post(f"/api/v1/interviews/{iid}/recordings?category=screen",headers=owner,
                  files={"file":("screen.webm",payload,"video/webm")})
    assert r.status_code==201,r.text
    rid=r.json()["id"]
    assert client.get("/api/v1/recordings/"+rid,headers=other).status_code==404
    assert client.get(f"/api/v1/interviews/{iid}/recordings",headers=other).status_code==404
    assert client.get("/api/v1/recordings/"+rid,headers=owner).status_code==200
    assert client.delete("/api/v1/recordings/"+rid,headers=owner).status_code==204
    assert client.get("/api/v1/recordings/"+rid,headers=owner).status_code==404

def test_face_requires_authentication_and_consent():
    img=("frame.jpg",b"\xff\xd8\xff"+b"test","image/jpeg")
    assert client.post("/api/v1/face/detect",files={"image":img}).status_code==401
    auth=headers()
    r=client.post("/api/v1/face/verify",headers=auth,
                  files={"enrollment":img,"live":img},data={"consent":"false"})
    assert r.status_code==400
