from fastapi import FastAPI

from app.routers import auth, music, subscriptions

app = FastAPI(title="Music Subscription Backend")

app.include_router(auth.router)
app.include_router(music.router)
app.include_router(subscriptions.router)
