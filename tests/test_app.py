import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from main import app
from app.db.database import Base, get_db

engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

def test_create_request_and_explain():
    with TestClient(app) as client:
        payload = {
            "subject": "Broken item",
            "description": "My item arrived completely shattered",
            "customer_id": "cust_123"
        }
        
        response = client.post("/api/requests", json=payload, headers={"idempotency-key": "key-123"})
        assert response.status_code == 202
        data = response.json()
        req_id = data["request_id"]
        
        response2 = client.post("/api/requests", json=payload, headers={"idempotency-key": "key-123"})
        assert response2.status_code == 202
        assert response2.json()["request_id"] == req_id
        
        time.sleep(2)
        
        exp_res = client.get(f"/api/requests/{req_id}/explain")
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        assert exp_data["request_id"] == req_id
        assert exp_data["current_state"] in ["MANUAL_REVIEW", "SUCCESS"]
    
def test_create_rule():
    with TestClient(app) as client:
        payload = {
            "name": "Low Confidence Review",
            "condition": {"field": "confidence", "operator": "<", "value": 0.5},
            "action": "manual_review"
        }
        response = client.post("/api/rules", json=payload)
        assert response.status_code == 200
        assert response.json()["name"] == "Low Confidence Review"
