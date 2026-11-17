from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Post, RoutingLog, Agent
from backend.app.schemas import RoutingExplanationResponse, RoutingLogItem

router = APIRouter(prefix="/api/v1/routing", tags=["Routing"])

@router.get("/explain/{post_id}", response_model=RoutingExplanationResponse)
def explain_routing(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    logs = db.query(RoutingLog).filter(RoutingLog.post_id == post_id).all()
    total_agents = db.query(Agent).count()

    eval_items = []
    stage1_passed_count = 0
    stage2_top_k_count = 0
    stage3_notified_count = 0

    # Sort evaluations so NOTIFIED comes first, then by rerank_score/vector_score descending
    sorted_logs = sorted(
        logs,
        key=lambda l: (1 if l.decision == "NOTIFIED" else 0, l.rerank_score, l.vector_score),
        reverse=True
    )

    for l in sorted_logs:
        target = l.target_agent
        if l.stage1_passed:
            stage1_passed_count += 1
        if l.decision in ("NOTIFIED", "REJECTED_STAGE3"):
            stage2_top_k_count += 1
        if l.decision == "NOTIFIED":
            stage3_notified_count += 1

        eval_items.append(
            RoutingLogItem(
                id=l.id,
                target_agent_id=l.target_agent_id,
                target_company=target.company_name if target else "Unknown",
                target_industry=target.industry_category if target else "General",
                stage1_passed=l.stage1_passed,
                stage1_reason=l.stage1_reason or "",
                vector_score=round(l.vector_score, 3),
                rerank_score=round(l.rerank_score, 3),
                rerank_rationale=l.rerank_rationale or "",
                decision=l.decision,
                status=l.status,
                created_at=l.created_at
            )
        )

    author = post.author_agent
    return RoutingExplanationResponse(
        post_id=post.id,
        post_title=post.title,
        author_company=author.company_name if author else "Unknown",
        total_registered_agents=total_agents,
        stage1_eligible_count=stage1_passed_count,
        stage2_top_k_count=stage2_top_k_count,
        stage3_notified_count=stage3_notified_count,
        evaluations=eval_items
    )
