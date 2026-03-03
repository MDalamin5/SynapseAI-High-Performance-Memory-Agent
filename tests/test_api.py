from fastapi.testclient import TestClient
from main import app

# Note: Ideally you mock the DB and OpenAI calls for unit tests.
# This is an Integration Test assuming local DB is running.

client = TestClient(app)

def test_chat_flow():
    # 1. Send first message
    payload = {
        "user_id": "test_user_api",
        "thread_id": "thread_api_1",
        "message": "My name is John and I love Pizza."
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    assert "John" in response.json()["response"] or "Pizza" in response.json()["response"]

    # 2. Verify LTM memory usage
    payload_query = {
        "user_id": "test_user_api",
        "thread_id": "thread_api_1",
        "message": "What is my favorite food?"
    }
    response_query = client.post("/api/v1/chat", json=payload_query)
    assert response_query.status_code == 200
    assert "Pizza" in response_query.json()["response"]