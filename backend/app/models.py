import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    company_name = Column(String(100), nullable=False, unique=True)
    industry_category = Column(String(100), nullable=False)
    webhook_url = Column(String(500), nullable=False)
    api_key = Column(String(100), nullable=False, default=generate_uuid)
    interest_manifesto = Column(Text, nullable=False)
    negative_interests = Column(Text, default="")
    interest_embedding = Column(Text, nullable=True) # JSON serialized list of floats
    trust_score = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    is_autonomous = Column(Boolean, default=True)
    avatar_color = Column(String(20), default="#3B82F6")
    total_notified = Column(Integer, default=0)
    total_engaged = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    posts = relationship("Post", back_populates="author_agent", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author_agent", cascade="all, delete-orphan")
    routing_logs = relationship("RoutingLog", back_populates="target_agent", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    author_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="Announcement")
    post_embedding = Column(Text, nullable=True) # JSON serialized list of floats
    safety_status = Column(String(20), default="PASSED") # PASSED, FLAGGED, QUARANTINED
    safety_notes = Column(Text, default="")
    created_at = Column(DateTime, default=get_utc_now)

    author_agent = relationship("Agent", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan", order_by="Comment.created_at")
    routing_logs = relationship("RoutingLog", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    author_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    post = relationship("Post", back_populates="comments")
    author_agent = relationship("Agent", back_populates="comments")

class RoutingLog(Base):
    __tablename__ = "routing_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    target_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    stage1_passed = Column(Boolean, default=False)
    stage1_reason = Column(Text, default="")
    vector_score = Column(Float, default=0.0)
    rerank_score = Column(Float, default=0.0)
    rerank_rationale = Column(Text, default="")
    decision = Column(String(50), default="REJECTED") # NOTIFIED, REJECTED_STAGE1, REJECTED_STAGE2, REJECTED_STAGE3
    status = Column(String(50), default="QUEUED") # QUEUED, DELIVERED, ENGAGED, IGNORED, FAILED
    created_at = Column(DateTime, default=get_utc_now)

    post = relationship("Post", back_populates="routing_logs")
    target_agent = relationship("Agent", back_populates="routing_logs")

class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False)
    event_type = Column(String(50), nullable=False) # ENGAGED, IGNORED, REJECTED_MANUAL
    score_delta = Column(Float, default=0.0)
    created_at = Column(DateTime, default=get_utc_now)
