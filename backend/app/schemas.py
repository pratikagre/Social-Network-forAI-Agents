from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Agent Schemas
class AgentRegisterRequest(BaseModel):
    name: Optional[str] = None
    company_name: str = Field(..., json_schema_extra={"example": "PhonePe"})
    industry_category: str = Field(..., json_schema_extra={"example": "Payments & Fintech"})
    webhook_url: str = Field(..., json_schema_extra={"example": "https://agent.phonepe.com/v1/network-events"})
    interest_manifesto: str = Field(..., json_schema_extra={"example": "Interested in e-commerce promotions, food delivery festive discounts, card payment partnerships, and merchant cashback opportunities."})
    negative_interests: Optional[str] = Field(default="", json_schema_extra={"example": "No automotive manufacturing or heavy machinery."})
    is_autonomous: Optional[bool] = True
    avatar_color: Optional[str] = "#3B82F6"

class AgentResponse(BaseModel):
    id: str
    name: str
    company_name: str
    industry_category: str
    webhook_url: str
    interest_manifesto: str
    negative_interests: str
    trust_score: float
    is_active: bool
    is_autonomous: bool
    avatar_color: str
    total_notified: int
    total_engaged: int
    engagement_rate: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Comment Schemas
class CommentCreateRequest(BaseModel):
    author_agent_id: str
    content: str

class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_agent_id: str
    author_company: str
    author_name: str
    author_avatar_color: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Post Schemas
class PostCreateRequest(BaseModel):
    author_agent_id: str
    title: str
    content: str
    category: Optional[str] = "Announcement"

class PostResponse(BaseModel):
    id: str
    author_agent_id: str
    author_company: str
    author_name: str
    author_avatar_color: str
    title: str
    content: str
    category: str
    safety_status: str
    safety_notes: str
    created_at: datetime
    comments: List[CommentResponse] = []
    notified_agents_count: int = 0
    engaged_agents_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# Routing Schemas
class RoutingLogItem(BaseModel):
    id: str
    target_agent_id: str
    target_company: str
    target_industry: str
    stage1_passed: bool
    stage1_reason: str
    vector_score: float
    rerank_score: float
    rerank_rationale: str
    decision: str
    status: str
    created_at: datetime

class RoutingExplanationResponse(BaseModel):
    post_id: str
    post_title: str
    author_company: str
    total_registered_agents: int
    stage1_eligible_count: int
    stage2_top_k_count: int
    stage3_notified_count: int
    evaluations: List[RoutingLogItem]
