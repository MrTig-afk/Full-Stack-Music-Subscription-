from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    user_name: str
    password: str


class SearchRequest(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    artist: Optional[str] = None
    album: Optional[str] = None


class SubscribeRequest(BaseModel):
    user_email: EmailStr
    title: str
    artist: str
    year: str
    album: str
    img_url: str


class RemoveSubscriptionRequest(BaseModel):
    user_email: EmailStr
    title: str
    album: str
