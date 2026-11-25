"""Regression coverage for fixed interview sequencing and authorization."""
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def register():
    import uuid
    value=uuid.uuid4().hex[:12]
    response=client.post("/api/v1/auth/register",json={"name":"Candidate Test","email":f"{value}@example.com","password":"A-long-test-password-123"})
    assert response.status_code==201,response.text
    return {"Authorization":"Bearer "+response.json()["access_token"]}

def test_exact_question_count_and_order_validation():
    headers=register()
    result=client.post("/api/v1/interviews",headers=headers,json={"target_role":"Software Developer","interview_type":"Technical","difficulty":"intermediate","question_count":10})
    assert result.status_code==201,result.text
    interview=result.json()
    assert len(interview["questions"])==10
    fetched=client.get(f"/api/v1/interviews/{interview['id']}",headers=headers)
    assert len(fetched.json()["questions"])==10
    first=interview["questions"][0]
    bad=client.post(f"/api/v1/interviews/{interview['id']}/answers",headers=headers,json={"question_id":first["id"],"question_text":"A different question from the one assigned","answer_text":"My response"})
    assert bad.status_code==422
    early=client.post(f"/api/v1/interviews/{interview['id']}/complete",headers=headers)
    assert early.status_code==409
    for q in interview["questions"]:
        answer=client.post(f"/api/v1/interviews/{interview['id']}/answers",headers=headers,json={"question_id":q["id"],"question_text":q["prompt"],"answer_text":"I would evaluate security, test assumptions and review the system carefully."})
        assert answer.status_code==201,answer.text
    completed=client.post(f"/api/v1/interviews/{interview['id']}/complete",headers=headers)
    assert completed.status_code==200,completed.text
    assert completed.json()["responses_count"]==10

def test_interview_owner_is_enforced():
    first=register()
    second=register()
    created=client.post("/api/v1/interviews",headers=first,json={"target_role":"Software Developer","question_count":3})
    assert created.status_code==201
    iid=created.json()["id"]
    assert client.get(f"/api/v1/interviews/{iid}",headers=second).status_code==404
