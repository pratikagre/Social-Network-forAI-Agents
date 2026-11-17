from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Post, Comment, Agent
from backend.app.schemas import CommentCreateRequest, CommentResponse
from backend.app.feedback import apply_positive_engagement

router = APIRouter(prefix="/api/v1/posts", tags=["Comments"])

def _to_comment_response(comment: Comment) -> CommentResponse:
    author = comment.author_agent
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author_agent_id=comment.author_agent_id,
        author_company=author.company_name if author else "Unknown",
        author_name=author.name if author else "Agent",
        author_avatar_color=author.avatar_color if author else "#6B7280",
        content=comment.content,
        created_at=comment.created_at
    )

@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(post_id: str, req: CommentCreateRequest, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    agent = db.query(Agent).filter(Agent.id == req.author_agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author agent not found.")

    new_comment = Comment(
        post_id=post_id,
        author_agent_id=req.author_agent_id,
        content=req.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    # Closed-loop feedback update
    apply_positive_engagement(db, post_id, req.author_agent_id)

    return _to_comment_response(new_comment)

@router.get("/{post_id}/comments", response_model=List[CommentResponse])
def list_comments(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at).all()
    return [_to_comment_response(c) for c in comments]
