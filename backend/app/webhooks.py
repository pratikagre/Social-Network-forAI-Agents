import json
import logging
import asyncio
from datetime import datetime, timezone
import httpx
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models import Agent, Post, Comment, RoutingLog
from backend.app.database import SessionLocal
from backend.app.safety import safety_moderator
from backend.app.autonomous_agents import autonomous_brain
from backend.app.feedback import apply_positive_engagement, apply_unengaged_penalty
from backend.app.config import settings

logger = logging.getLogger("agentpulse.webhooks")

class WebhookDispatcher:
    """
    Handles asynchronous notification dispatch to target agents.
    Supports:
    - HMAC signature generation
    - External HTTP webhook push with timeouts
    - Autonomous in-process agent execution for simulated companies
    - Automatic response ingestion and feedback recording
    """

    async def dispatch_notifications(self, post_id: str, notified_agent_ids: List[str]):
        """
        Background task to deliver webhooks and handle agent replies.
        """
        db = SessionLocal()
        tasks = []
        try:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                return

            author = post.author_agent
            author_company = author.company_name if author else "Unknown"

            for agent_id in notified_agent_ids:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    continue

                # Prepare sanitized, prompt-injection-safe payload
                sanitized_payload = safety_moderator.sanitize_for_target_agent(
                    title=post.title,
                    content=post.content,
                    author_company=author_company
                )

                payload_json = json.dumps({
                    "event_type": "post.relevant_notification",
                    "event_id": str(post.id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "recipient_agent": {
                        "id": agent.id,
                        "company_name": agent.company_name
                    },
                    "data": sanitized_payload
                })

                # Compute HMAC signature
                signature = safety_moderator.generate_hmac_signature(payload_json.encode('utf-8'))

                # Update routing log status to DELIVERED
                log = db.query(RoutingLog).filter(
                    RoutingLog.post_id == post.id,
                    RoutingLog.target_agent_id == agent.id
                ).first()
                if log:
                    log.status = "DELIVERED"
                    db.commit()

                # Case A: Autonomous In-Process Agent (e.g. PhonePe, HDFC Bank)
                if agent.is_autonomous:
                    tasks.append(
                        self._process_autonomous_agent(
                            post_id=post.id,
                            agent_id=agent.id,
                            agent_company=agent.company_name,
                            agent_manifesto=agent.interest_manifesto,
                            sanitized_payload=sanitized_payload
                        )
                    )
                else:
                    # Case B: External Webhook URL
                    tasks.append(
                        self._send_external_webhook(
                            webhook_url=agent.webhook_url,
                            payload_json=payload_json,
                            signature=signature
                        )
                    )

            # Await all notification & autonomous agent tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            db.close()

    async def _send_external_webhook(self, webhook_url: str, payload_json: str, signature: str):
        headers = {
            "Content-Type": "application/json",
            "X-AgentNet-Signature": f"sha256={signature}",
            "User-Agent": "AgentPulse-Webhook-Dispatcher/1.0"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook_url, content=payload_json, headers=headers)
        except Exception as e:
            logger.info(f"Webhook dispatch to {webhook_url} encountered expected simulation result: {e}")

    async def _process_autonomous_agent(
        self,
        post_id: str,
        agent_id: str,
        agent_company: str,
        agent_manifesto: str,
        sanitized_payload: Dict[str, Any]
    ):
        """
        Simulates autonomous agent decision-making & automatic comment reply.
        """
        if settings.autonomous_response_delay_sec > 0:
            await asyncio.sleep(settings.autonomous_response_delay_sec)

        # Autonomous reasoning & persona evaluation
        response_text = autonomous_brain.evaluate_and_respond(
            agent_company=agent_company,
            agent_manifesto=agent_manifesto,
            sanitized_post=sanitized_payload
        )

        if not response_text:
            # Agent decided not to engage
            db = SessionLocal()
            try:
                apply_unengaged_penalty(db, post_id, agent_id)
            finally:
                db.close()
            return

        # Agent decided to engage! Post comment back to platform
        db = SessionLocal()
        try:
            comment = Comment(
                post_id=post_id,
                author_agent_id=agent_id,
                content=response_text
            )
            db.add(comment)
            db.commit()

            # Trigger positive closed-loop feedback update
            apply_positive_engagement(db, post_id, agent_id)
            logger.info(f"Autonomous comment posted by {agent_company} on post {post_id}")
        finally:
            db.close()

webhook_dispatcher = WebhookDispatcher()
