import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Agent
from backend.app.schemas import AgentRegisterRequest, AgentResponse
from backend.app.embeddings import embedding_engine

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])

def _to_agent_response(agent: Agent) -> AgentResponse:
    rate = (agent.total_engaged / agent.total_notified) if agent.total_notified > 0 else 0.0
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        company_name=agent.company_name,
        industry_category=agent.industry_category,
        webhook_url=agent.webhook_url,
        interest_manifesto=agent.interest_manifesto,
        negative_interests=agent.negative_interests or "",
        trust_score=agent.trust_score,
        is_active=agent.is_active,
        is_autonomous=agent.is_autonomous,
        avatar_color=agent.avatar_color,
        total_notified=agent.total_notified,
        total_engaged=agent.total_engaged,
        engagement_rate=round(rate, 2),
        created_at=agent.created_at
    )

@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def register_agent(req: AgentRegisterRequest, db: Session = Depends(get_db)):
    # Check if company already registered
    existing = db.query(Agent).filter(Agent.company_name == req.company_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent for company '{req.company_name}' is already registered."
        )

    # Embed interest manifesto
    interest_vec = embedding_engine.embed_text(req.interest_manifesto)

    agent_name = req.name or f"{req.company_name} Agent"
    new_agent = Agent(
        name=agent_name,
        company_name=req.company_name,
        industry_category=req.industry_category,
        webhook_url=req.webhook_url,
        interest_manifesto=req.interest_manifesto,
        negative_interests=req.negative_interests or "",
        interest_embedding=json.dumps(interest_vec),
        is_autonomous=req.is_autonomous if req.is_autonomous is not None else True,
        avatar_color=req.avatar_color or "#3B82F6"
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return _to_agent_response(new_agent)

@router.get("", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).order_by(Agent.company_name).all()
    return [_to_agent_response(a) for a in agents]

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return _to_agent_response(agent)
