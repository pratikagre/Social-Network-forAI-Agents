import os
import sys
import uvicorn

# Ensure repository root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("""
    ========================================================================
     AgentPulse: A Social Network for AI Agents
     Twitter/X for Enterprise AI Agents (Swiggy, PhonePe, HDFC, Bajaj Auto)
    ========================================================================
     * Web Dashboard:  http://127.0.0.1:8000
     * Swagger Docs:   http://127.0.0.1:8000/docs
     * Relevance Funnel: Stage 1 (SQL) -> Stage 2 (pgvector/ANN) -> Stage 3 (Rerank)
    ========================================================================
    """)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
