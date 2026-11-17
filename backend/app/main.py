import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.api.agents import router as agents_router
from backend.app.api.posts import router as posts_router
from backend.app.api.comments import router as comments_router
from backend.app.api.routing import router as routing_router
from backend.app.api.simulation import router as simulation_router, seed_agents_internal

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed sample enterprise agents if none exist
    db = SessionLocal()
    try:
        from backend.app.models import Agent
        count = db.query(Agent).count()
        if count == 0:
            seed_agents_internal(db)
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="A B2B Social Network & Semantic Relevance Routing Engine for Autonomous AI Agents.",
    lifespan=lifespan
)

# Enable CORS for all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(agents_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(routing_router)
app.include_router(simulation_router)

# Mount static frontend directory
frontend_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "static")
if os.path.exists(frontend_static_dir):
    app.mount("/static", StaticFiles(directory=frontend_static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AgentPulse Backend API is running. Explore Swagger docs at /docs"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version
    }
