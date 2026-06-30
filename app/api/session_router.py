"""Session management router."""

from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["Sessions"])
