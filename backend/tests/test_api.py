import uuid
import pytest
from fastapi.testclient import TestClient
from app import main

@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate each test so no local/developer database is modified.
    monkeypatch.setattr(main, "DATABASE_PATH", tmp_path / "test.db")
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client

def register(client):
    email = f"{uuid.uuid4().hex}@example.test"
    response = client.post("/api/v1/auth/register", json={
        "name": "Test Candidate", "email": email, "password": "safe-test-password-123"
    })
    assert response.status_code == 201, response.text
    return response.json()["access_token"]

def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_protected_profile_requires_token(client):
    assert client.get("/api/v1/profile").status_code == 401

def test_questions_requires_authentication(client):
    assert client.get("/api/v1/questions").status_code == 401

def test_candidate_can_complete_interview_and_read_scored_report(client):
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}

    questions = client.get("/api/v1/questions", headers=headers)
    assert questions.status_code == 200
    assert questions.json(), "Seed question bank should not be empty"
    question = questions.json()[0]

    started = client.post("/api/v1/interviews", headers=headers, json={
        "title": "End-to-end test", "target_role": "Software Developer",
        "interview_type": "Mixed", "difficulty": "beginner", "question_count": 1
    })
    assert started.status_code == 201, started.text
    interview = started.json()
    assert interview["questions"], "Interview should include at least one question"
    question = interview["questions"][0]

    submitted = client.post(
        f"/api/v1/interviews/{interview['id']}/answers",
        headers=headers,
        json={
            "question_id": question["id"],
            "question_text": question["prompt"],
            "answer_text": (
                "I would first understand the problem and requirements, then make a plan. "
                "I would implement the solution, test the result, discuss trade-offs with "
                "the team, and document what I learned from the outcome."
            )
        },
    )
    assert submitted.status_code == 201, submitted.text
    scores = submitted.json()
    assert 0 <= scores["relevance"] <= 100
    assert 0 <= scores["completeness"] <= 100
    assert 0 <= scores["clarity"] <= 100
    assert scores["evaluation_method"] == "transparent_baseline_rubric"

    completed = client.post(f"/api/v1/interviews/{interview['id']}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["responses_count"] == 1

    report = client.get(f"/api/v1/reports/{interview['id']}", headers=headers)
    assert report.status_code == 200, report.text
    assert report.json()["overall_score"] >= 0
    assert len(report.json()["responses"]) == 1
    assert report.json()["evaluation_method"] == "transparent_baseline_rubric"

def test_candidate_cannot_read_another_candidates_interview(client):
    token_a = register(client)
    token_b = register(client)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    started = client.post("/api/v1/interviews", headers=headers_a, json={
        "title": "Private session", "target_role": "Software Developer",
        "interview_type": "Mixed", "difficulty": "beginner", "question_count": 1
    })
    assert started.status_code == 201
    interview_id = started.json()["id"]
    assert client.get(f"/api/v1/interviews/{interview_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/reports/{interview_id}", headers=headers_b).status_code == 404
