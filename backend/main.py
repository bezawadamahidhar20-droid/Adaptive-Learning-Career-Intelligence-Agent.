"""
FastAPI Server Entrypoint for Adaptive Learning & Career Intelligence Agent
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure agent package is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routers import auth, career, assessment, dashboard
from backend.database import init_db
from agent.analytics.train_calibration import ensure_calibration_artifact

app = FastAPI(
    title="Adaptive Learning & Career Intelligence Agent API",
    description="LLM-free AI/ML adaptive testing platform powered by BKT, IRT, Bandits & Career Matching.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(career.router, prefix="/api")
app.include_router(assessment.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# Mount Static frontend files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_path = os.path.join(frontend_dir, "index.html")
        return FileResponse(index_path)

@app.on_event("startup")
def on_startup():
    init_db()
    # Self-heal the calibration artifact: on a fresh checkout the agent would otherwise
    # silently run on built-in BKT defaults instead of the calibrated parameters.
    ensure_calibration_artifact()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "agent_engine": "BKT+IRT+Bandits", "version": "1.0.0"}
