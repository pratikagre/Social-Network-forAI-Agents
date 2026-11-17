import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Agent, Post, Comment
from backend.app.config import settings

client = TestClient(app)

def test_full_diwali_flow_end_to_end():
    # Set zero delay during test execution
    settings.autonomous_response_delay_sec = 0.0

    # 1. Reset database
    res_reset = client.post("/api/v1/simulation/reset")
    assert res_reset.status_code == 200

    # 2. Trigger Diwali scenario
    demo_res = client.post("/api/v1/simulation/diwali-demo")
    assert demo_res.status_code == 200
    demo_data = demo_res.json()
    post_id = demo_data["post_id"]

    assert "PhonePe" in demo_data["notified_agents"]
    assert "HDFC Bank" in demo_data["notified_agents"]
    assert "Bajaj Auto" in demo_data["excluded_agents"]

    # 3. Fetch the post and its thread
    post_res = client.get(f"/api/v1/posts/{post_id}")
    assert post_res.status_code == 200
    post_feed = post_res.json()

    assert post_feed["title"] == "Diwali Food Delivery Discount"
    assert post_feed["author_company"] == "Swiggy"

    # Comments from PhonePe and HDFC Bank
    comments = post_feed["comments"]
    commenting_companies = [c["author_company"] for c in comments]
    
    assert "PhonePe" in commenting_companies
    assert "HDFC Bank" in commenting_companies
    # Verify Bajaj Auto never commented
    assert "Bajaj Auto" not in commenting_companies
