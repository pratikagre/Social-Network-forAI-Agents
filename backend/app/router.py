import json
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.models import Agent, Post, RoutingLog
from backend.app.embeddings import embedding_engine
from backend.app.reranker import reranker
from backend.app.config import settings

logger = logging.getLogger("agentpulse.router")

class MultiStageRelevanceRouter:
    """
    Core Relevance Routing Engine:
    Stage 1: SQL Rule Guardrails (Author exclusion, active status, trust filters)
    Stage 2: Dense Semantic Vector Cosine Match (Top-K ANN Retrieval)
    Stage 3: Cross-Encoder & Commercial Synergy Reranker (S_final >= 0.75)
    """

    def route_post(self, db: Session, post: Post) -> List[Agent]:
        """
        Executes the 3-stage candidate filtering pipeline on a newly published post.
        Saves full evaluation logs in routing_logs and returns notified agents.
        """
        author = post.author_agent
        if not author:
            author = db.query(Agent).filter(Agent.id == post.author_agent_id).first()

        # Step 0: Ensure post has an embedding
        if not post.post_embedding:
            post_embed = embedding_engine.embed_text(f"{post.title} {post.content}")
            post.post_embedding = json.dumps(post_embed)
            db.commit()
        else:
            post_embed = json.loads(post.post_embedding)

        # -------------------------------------------------------------
        # STAGE 1: Fast SQL Metadata Guardrails
        # -------------------------------------------------------------
        # Fetch all candidate agents except the post author
        all_agents = db.query(Agent).all()
        stage1_candidates: List[Agent] = []

        for agent in all_agents:
            if agent.id == post.author_agent_id:
                # Exclude author from self-notification
                self._record_log(
                    db, post.id, agent.id,
                    stage1_passed=False,
                    stage1_reason="Author self-exclusion rule.",
                    vector_score=0.0,
                    rerank_score=0.0,
                    rationale="Author agent is excluded from receiving notifications for its own post.",
                    decision="REJECTED_STAGE1",
                    status="IGNORED"
                )
                continue

            if not agent.is_active:
                self._record_log(
                    db, post.id, agent.id,
                    stage1_passed=False,
                    stage1_reason="Agent inactive or suspended.",
                    vector_score=0.0,
                    rerank_score=0.0,
                    rationale="Agent is currently disabled or suspended.",
                    decision="REJECTED_STAGE1",
                    status="IGNORED"
                )
                continue

            if agent.trust_score < 0.2:
                self._record_log(
                    db, post.id, agent.id,
                    stage1_passed=False,
                    stage1_reason="Low trust score threshold quarantine.",
                    vector_score=0.0,
                    rerank_score=0.0,
                    rationale="Agent trust score below minimum safety floor (0.2).",
                    decision="REJECTED_STAGE1",
                    status="IGNORED"
                )
                continue

            stage1_candidates.append(agent)

        # -------------------------------------------------------------
        # STAGE 2: Dense Semantic Vector Match (Top-K ANN)
        # -------------------------------------------------------------
        scored_candidates: List[Tuple[Agent, float]] = []

        for agent in stage1_candidates:
            if not agent.interest_embedding:
                agent_vec = embedding_engine.embed_text(agent.interest_manifesto)
                agent.interest_embedding = json.dumps(agent_vec)
                db.commit()
            else:
                agent_vec = json.loads(agent.interest_embedding)

            v_score = embedding_engine.cosine_similarity(post_embed, agent_vec)
            scored_candidates.append((agent, v_score))

        # Sort descending by vector cosine similarity
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Take Top K (default 50)
        top_k_candidates = scored_candidates[:settings.stage2_top_k]
        dropped_stage2 = scored_candidates[settings.stage2_top_k:]

        for agent, v_score in dropped_stage2:
            self._record_log(
                db, post.id, agent.id,
                stage1_passed=True,
                stage1_reason="Eligible active agent.",
                vector_score=round(v_score, 3),
                rerank_score=0.0,
                rationale=f"Dense vector score ({v_score:.3f}) below Top-K cutoff rank ({settings.stage2_top_k}).",
                decision="REJECTED_STAGE2",
                status="IGNORED"
            )

        # -------------------------------------------------------------
        # STAGE 3: Cross-Encoder / Commercial Synergy Reranker & LLM Filter
        # -------------------------------------------------------------
        final_notified_agents: List[Agent] = []

        for agent, v_score in top_k_candidates:
            rerank_score, rationale, is_notified = reranker.evaluate(
                post_title=post.title,
                post_content=post.content,
                author_company=author.company_name if author else "Unknown",
                author_industry=author.industry_category if author else "General",
                target_agent=agent,
                vector_score=v_score
            )

            if is_notified:
                decision = "NOTIFIED"
                status = "QUEUED"
                final_notified_agents.append(agent)
                # Increment agent total_notified counter
                agent.total_notified += 1
            else:
                decision = "REJECTED_STAGE3"
                status = "IGNORED"

            self._record_log(
                db, post.id, agent.id,
                stage1_passed=True,
                stage1_reason="Passed rule filters.",
                vector_score=round(v_score, 3),
                rerank_score=rerank_score,
                rationale=rationale,
                decision=decision,
                status=status
            )

        db.commit()
        return final_notified_agents

    def _record_log(
        self,
        db: Session,
        post_id: str,
        target_agent_id: str,
        stage1_passed: bool,
        stage1_reason: str,
        vector_score: float,
        rerank_score: float,
        rationale: str,
        decision: str,
        status: str
    ):
        log = RoutingLog(
            post_id=post_id,
            target_agent_id=target_agent_id,
            stage1_passed=stage1_passed,
            stage1_reason=stage1_reason,
            vector_score=vector_score,
            rerank_score=rerank_score,
            rerank_rationale=rationale,
            decision=decision,
            status=status
        )
        db.add(log)

routing_engine = MultiStageRelevanceRouter()
