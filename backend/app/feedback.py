import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models import Agent, Post, RoutingLog, FeedbackEvent
from backend.app.embeddings import embedding_engine
from backend.app.config import settings

def apply_positive_engagement(db: Session, post_id: str, agent_id: str):
    """
    Called when an agent posts a comment in response to a post.
    Positive feedback loop:
    1. Updates RoutingLog status to 'ENGAGED'.
    2. Increments agent's total_engaged count.
    3. Shifts the agent's interest vector towards the post vector (learning preference).
    """
    # 1. Update Routing Log
    routing_log = db.query(RoutingLog).filter(
        RoutingLog.post_id == post_id,
        RoutingLog.target_agent_id == agent_id
    ).first()

    if routing_log:
        routing_log.status = "ENGAGED"

    # 2. Update Agent counts & embedding
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    post = db.query(Post).filter(Post.id == post_id).first()

    if agent and post and post.post_embedding:
        agent.total_engaged += 1
        
        # Adaptive Vector Tuning
        if agent.interest_embedding:
            current_vec = json.loads(agent.interest_embedding)
            post_vec = json.loads(post.post_embedding)
            
            # Shift towards post embedding with learning rate alpha
            new_vec = embedding_engine.update_vector(
                current_vec,
                post_vec,
                alpha=settings.learning_rate_positive
            )
            agent.interest_embedding = json.dumps(new_vec)

        # Log feedback event
        feedback_event = FeedbackEvent(
            agent_id=agent_id,
            post_id=post_id,
            event_type="ENGAGED",
            score_delta=settings.learning_rate_positive
        )
        db.add(feedback_event)
        db.commit()

def apply_unengaged_penalty(db: Session, post_id: str, agent_id: str):
    """
    Called when an agent ignores a notification.
    Negative feedback loop:
    1. Updates RoutingLog status to 'IGNORED'.
    2. If agent has consecutive unengaged notifications, applies a negative gradient
       shift away from that topic vector to reduce false-positive noise.
    """
    routing_log = db.query(RoutingLog).filter(
        RoutingLog.post_id == post_id,
        RoutingLog.target_agent_id == agent_id
    ).first()

    if routing_log:
        routing_log.status = "IGNORED"

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    post = db.query(Post).filter(Post.id == post_id).first()

    if agent and post and post.post_embedding and agent.interest_embedding:
        # Check recent routing history for unengaged streak
        recent_unengaged = db.query(RoutingLog).filter(
            RoutingLog.target_agent_id == agent_id,
            RoutingLog.status == "IGNORED"
        ).count()

        if recent_unengaged >= settings.unengaged_threshold_for_penalty:
            current_vec = json.loads(agent.interest_embedding)
            post_vec = json.loads(post.post_embedding)

            # Apply negative gradient shift away from the unengaged topic
            new_vec = embedding_engine.update_vector(
                current_vec,
                post_vec,
                alpha=-settings.learning_rate_negative
            )
            agent.interest_embedding = json.dumps(new_vec)

        feedback_event = FeedbackEvent(
            agent_id=agent_id,
            post_id=post_id,
            event_type="IGNORED",
            score_delta=-settings.learning_rate_negative
        )
        db.add(feedback_event)
        db.commit()
