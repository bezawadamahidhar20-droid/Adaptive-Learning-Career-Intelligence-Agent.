"""
FastAPI Server Entrypoint for Adaptive Learning & Career Intelligence Agent
Production-ready API with JWT auth, OAuth, Onboarding, Skills, Roadmaps & Placement.
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routers import (
    auth, onboarding, skills, career, roadmap, placement, assessment, dashboard
)
from backend.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database schema & tables
    init_db()
    yield

app = FastAPI(
    title="Adaptive Learning & Career Intelligence Agent API",
    description="LLM-free AI/ML adaptive testing & career intelligence platform powered by BKT, IRT, Bandits, and Multi-Agent sub-systems.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register All API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(career.router, prefix="/api")
app.include_router(roadmap.router, prefix="/api")
app.include_router(placement.router, prefix="/api")
app.include_router(assessment.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# Static frontend mounting
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_path = os.path.join(frontend_dir, "index.html")
        return FileResponse(index_path)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "agent_engine": "BKT+IRT+Bandits+MultiAgent",
        "version": "2.0.0",
        "auth_enabled": True
    }
