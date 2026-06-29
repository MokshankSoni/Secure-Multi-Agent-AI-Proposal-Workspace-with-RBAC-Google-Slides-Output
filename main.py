"""
Main application entry point.

Instantiates the FastAPI application and defines the root endpoint.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Secure Multi-Agent AI Proposal Workspace",
    description="Production-grade backend for an AI proposal generation system.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """
    Root endpoint for health check.
    """
    return {
        "status": "running",
        "project": "Secure Multi-Agent AI Proposal Workspace"
    }
