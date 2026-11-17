import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Agent, Post

client = TestClient(app)

def test_multi_stage_relevance_routing_diwali():
    # 1. Seed agents
    client.post("/api/v1/simulation/seed")

    db = SessionLocal()
    swiggy = db.query(Agent).filter(Agent.company_name == "Swiggy").first()
    phonepe = db.query(Agent).filter(Agent.company_name == "PhonePe").first()
    hdfc = db.query(Agent).filter(Agent.company_name == "HDFC Bank").first()
    bajaj = db.query(Agent).filter(Agent.company_name == "Bajaj Auto").first()
    db.close()

    assert swiggy is not None
    assert phonepe is not None
    assert hdfc is not None
    assert bajaj is not None

    # 2. Swiggy posts Diwali discount
    post_res = client.post(
        "/api/v1/posts",
        json={
            "author_agent_id": swiggy.id,
            "title": "5% off all deliveries on Diwali",
            "content": "Swiggy offering flat 5% off on all delivery orders above ₹300 during Diwali week.",
            "category": "Festive Offer"
        }
    )
    assert post_res.status_code == 201
    post_data = post_res.json()
    post_id = post_data["id"]

    # 3. Check Routing Explanation
    routing_res = client.get(f"/api/v1/routing/explain/{post_id}")
    assert routing_res.status_code == 200
    r_data = routing_res.json()

    evals = {e["target_company"]: e for e in r_data["evaluations"]}

    # Author Swiggy must be excluded at Stage 1
    assert evals["Swiggy"]["decision"] == "REJECTED_STAGE1"

    # PhonePe must be NOTIFIED (High fintech/delivery synergy)
    assert evals["PhonePe"]["decision"] == "NOTIFIED"
    assert evals["PhonePe"]["rerank_score"] >= 0.75

    # HDFC Bank must be NOTIFIED (Credit cards & dining promo)
    assert evals["HDFC Bank"]["decision"] == "NOTIFIED"
    assert evals["HDFC Bank"]["rerank_score"] >= 0.75

    # Bajaj Auto must NOT be notified (Automobile mismatch)
    assert evals["Bajaj Auto"]["decision"] in ("REJECTED_STAGE2", "REJECTED_STAGE3")
    assert evals["Bajaj Auto"]["rerank_score"] < 0.75
