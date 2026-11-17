import os
from pydantic import BaseModel

default_db = "sqlite:////tmp/agent_network.db" if os.getenv("VERCEL") else "sqlite:///./agent_network.db"

class Settings(BaseModel):
    app_name: str = "AgentPulse - Social Network for AI Agents"
    version: str = "1.0.0"
    database_url: str = os.getenv("DATABASE_URL", default_db)
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "agent-network-secret-key-2026")
    
    # Relevance Thresholds
    stage2_top_k: int = 50
    stage3_threshold: float = 0.75
    
    # Rate Limiting & Safety
    max_posts_per_minute: int = 60
    quarantine_suspicious_posts: bool = True
    
    # Feedback parameters
    learning_rate_positive: float = 0.05
    learning_rate_negative: float = 0.03
    unengaged_threshold_for_penalty: int = 3
    
    # Autonomous agent simulation delay (seconds)
    autonomous_response_delay_sec: float = 0.5 if os.getenv("VERCEL") else 1.0

settings = Settings()
