"""FastAPI application entrypoint for Music Subscription Backend.

This module initializes the FastAPI application with:
- CORS middleware for cross-origin frontend requests
- Authentication routes (login, register, logout)
- Music search routes (query by title, artist, album, year)
- Subscription management routes (add, remove, view user subscriptions)
- Health check endpoint for deployment verification

Environment Variables:
    FRONTEND_ORIGINS: Comma-separated list of allowed origins for CORS (default: '*')

Example:
    Start dev server: python -m app.main run_dev()
    Production: uvicorn app.main:app --host 0.0.0.0 --port 80
"""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, music, subscriptions

app = FastAPI(title="Music Subscription Backend")

# Parse CORS allowed origins from environment variable or use default wildcard.
# Format: comma-separated list (e.g., "http://example.com,http://other.com").
# Default: "*" (allow all origins, suitable for public APIs and development).
frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
]

# Configure CORS middleware to allow static frontend on separate origin to call this API.
# In production, narrow allow_origins to specific frontend URLs.
# Ref: <https://fastapi.tiangolo.com/tutorial/cors/#use-corsmiddleware>
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers for structured endpoint organization.
app.include_router(auth.router)
app.include_router(music.router)
app.include_router(subscriptions.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Health check endpoint to verify server is running.

    Returns:
        dict[str, str]: Simple JSON response indicating server status.
    """
    return {"status": "ok"}


def run_dev() -> None:
    """
    Run local dev server with local target and hot reloading
    """
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
