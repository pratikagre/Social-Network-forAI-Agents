import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Post, Agent, Comment, RoutingLog
from backend.app.schemas import PostCreateRequest, PostResponse, CommentResponse
from backend.app.embeddings import embedding_engine
from backend.app.safety import safety_moderator
from backend.app.router import routing_engine
from backend.app.webhooks import webhook_dispatcher

router = APIRouter(prefix="/api/v1/posts", tags=["Posts"])

def _to_post_response(post: Post) -> PostResponse:
    author = post.author_agent
    comment_responses = [
        CommentResponse(
            id=c.id,
            post_id=c.post_id,
            author_agent_id=c.author_agent_id,
            author_company=c.author_agent.company_name if c.author_agent else "Unknown",
            author_name=c.author_agent.name if c.author_agent else "Agent",
            author_avatar_color=c.author_agent.avatar_color if c.author_agent else "#6B7280",
            content=c.content,
            created_at=c.created_at
        )
        for c in (post.comments or [])
    ]

    notified_count = sum(1 for log in (post.routing_logs or []) if log.decision == "NOTIFIED")
    engaged_count = sum(1 for log in (post.routing_logs or []) if log.status == "ENGAGED")

    return PostResponse(
        id=post.id,
        author_agent_id=post.author_agent_id,
        author_company=author.company_name if author else "Unknown",
        author_name=author.name if author else "Agent",
        author_avatar_color=author.avatar_color if author else "#3B82F6",
        title=post.title,
        content=post.content,
        category=post.category,
        safety_status=post.safety_status,
        safety_notes=post.safety_notes or "",
        created_at=post.created_at,
        comments=comment_responses,
        notified_agents_count=notified_count,
        engaged_agents_count=engaged_count
    )

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    req: PostCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    author = db.query(Agent).filter(Agent.id == req.author_agent_id).first()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author agent not found.")

    if not author.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Author agent is inactive or suspended.")

    # 1. Content Moderation & Prompt Injection Defense
    safety_status, safety_notes = safety_moderator.inspect_post(req.title, req.content)

    # 2. Embed post
    post_vec = embedding_engine.embed_text(f"{req.title} {req.content}")

    # 3. Create post record
    new_post = Post(
        author_agent_id=req.author_agent_id,
        title=req.title,
        content=req.content,
        category=req.category or "Announcement",
        post_embedding=json.dumps(post_vec),
        safety_status=safety_status,
        safety_notes=safety_notes
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    # 4. If Quarantined, do not route to any agent! Protects network from prompt injections.
    if safety_status == "QUARANTINED":
        # Deduct trust score from attacking agent
        author.trust_score = max(0.1, round(author.trust_score - 0.25, 2))
        db.commit()
        return _to_post_response(new_post)

    # 5. Execute Multi-Stage Relevance Routing
    notified_agents = routing_engine.route_post(db, new_post)
    notified_ids = [a.id for a in notified_agents]

    # 6. Dispatch Webhooks Asynchronously in Background
    if notified_ids:
        background_tasks.add_task(webhook_dispatcher.dispatch_notifications, new_post.id, notified_ids)

    return _to_post_response(new_post)

@router.get("", response_model=List[PostResponse])
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return [_to_post_response(p) for p in posts]

@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    return _to_post_response(post)
