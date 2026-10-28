from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_is_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_protected_profile_requires_token():
    response = client.get("/api/v1/profile")
    assert response.status_code == 401

def test_questions_requires_authentication():
    response = client.get("/api/v1/questions")
    assert response.status_code == 401
