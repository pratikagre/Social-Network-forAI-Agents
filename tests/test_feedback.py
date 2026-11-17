import json
import pytest
from backend.app.database import SessionLocal
from backend.app.models import Agent, Post, RoutingLog, FeedbackEvent
from backend.app.feedback import apply_positive_engagement, apply_unengaged_penalty
from backend.app.embeddings import embedding_engine

def test_closed_loop_positive_feedback():
    db = SessionLocal()
    agent = db.query(Agent).filter(Agent.company_name == "PhonePe").first()
    
    # Create a mock post
    post_vec = embedding_engine.embed_text("Diwali food grocery cashback")
    post = Post(
        author_agent_id=agent.id,
        title="Test Festive Offer",
        content="Cashback on groceries",
        post_embedding=json.dumps(post_vec)
    )
    db.add(post)
    db.commit()

    # Create a mock routing log
    r_log = RoutingLog(
        post_id=post.id,
        target_agent_id=agent.id,
        stage1_passed=True,
        vector_score=0.7,
        rerank_score=0.8,
        decision="NOTIFIED",
        status="DELIVERED"
    )
    db.add(r_log)
    db.commit()

    initial_engaged = agent.total_engaged
    initial_vec = json.loads(agent.interest_embedding)

    # Apply positive engagement (agent commented)
    apply_positive_engagement(db, post.id, agent.id)

    db.refresh(agent)
    db.refresh(r_log)

    # Status must update to ENGAGED
    assert r_log.status == "ENGAGED"
    assert agent.total_engaged == initial_engaged + 1

    # Vector must have shifted
    updated_vec = json.loads(agent.interest_embedding)
    assert updated_vec != initial_vec

    db.close()
