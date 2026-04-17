from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    user_name: str
    password: str

class SearchRequest(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    artist: Optional[str] = None
    album: Optional[str] = None

class SubscribeRequest(BaseModel):
    user_email: str
    title: str
    artist: str
    year: str
    album: str
    img_url: str

class RemoveSubscriptionRequest(BaseModel):
    user_email: str
    title: str
    album: str