import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal, Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_agent_registration_and_embedding():
    response = client.post(
        "/api/v1/agents/register",
        json={
            "company_name": "Tata Neu",
            "industry_category": "Super App & Retail",
            "webhook_url": "https://agent.tataneu.com/events",
            "interest_manifesto": "Interested in airline points, luxury shopping, grocery loyalty, and financial services.",
            "negative_interests": "No industrial chemicals."
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Tata Neu"
    assert data["trust_score"] == 1.0
    assert data["is_active"] is True

def test_prevent_duplicate_agent():
    # Registering same company again should fail
    response = client.post(
        "/api/v1/agents/register",
        json={
            "company_name": "Tata Neu",
            "industry_category": "Super App & Retail",
            "webhook_url": "https://agent.tataneu.com/events2",
            "interest_manifesto": "Duplicate test."
        }
    )
    assert response.status_code == 409
