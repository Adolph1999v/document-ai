"""Backward-compatible ASGI entry point.

Run locally with: uvicorn main:app --reload
"""

from app.main import app

__all__ = ["app"]
