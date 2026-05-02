import uvicorn
from fastapi import FastAPI

from app.routers import auth, music, subscriptions

app = FastAPI(title="Music Subscription Backend")

app.include_router(auth.router)
app.include_router(music.router)
app.include_router(subscriptions.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def run_dev() -> None:
    """
    Run local dev server with the same target as README.
    """
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
