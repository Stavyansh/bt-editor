"""
FastAPI Application for Behavior Tree Editor.
Serves API and static files for web visualizer.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router

app = FastAPI(
    title="Behavior Tree Editor API",
    description="REST API for executing and visualizing behavior trees",
    version="0.1.0"
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve the web visualizer."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Behavior Tree Editor API", "docs": "/docs", "visualizer": "not built yet"}


@app.get("/api")
async def api_root():
    """API root with links."""
    return {
        "message": "Behavior Tree Editor API",
        "endpoints": {
            "examples": "/api/examples",
            "run_tree": "/api/run-tree",
            "run_tree_file": "/api/run-tree-file/{filename}",
            "tree_structure": "/api/tree-structure/{filename}",
            "health": "/api/health",
        },
        "docs": "/docs"
    }
