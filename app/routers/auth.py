from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.db import login_table
from app.schemas import LoginRequest, RegisterRequest

router = APIRouter()


@router.post("/login")
def login_user(payload: LoginRequest):
    result = login_table.get_item(Key={"email": payload.email})
    user = result.get("Item")

    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="email or password is invalid")

    user_name = str(user["user_name"])
    user_email = str(user["email"])

    response = JSONResponse(
        content={
            "message": "Login successful",
            "user_name": user_name,
            "email": user_email,
        }
    )
    response.set_cookie("user_email", user_email)
    response.set_cookie("user_name", user_name)
    return response


@router.post("/register")
def register_user(payload: RegisterRequest):
    result = login_table.get_item(Key={"email": payload.email})

    if "Item" in result:
        raise HTTPException(status_code=400, detail="The email already exists")

    login_table.put_item(
        Item={
            "email": payload.email,
            "user_name": payload.user_name,
            "password": payload.password,
        }
    )

    return {"message": "Registered successfully"}


@router.get("/logout")
def logout_user():
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("user_email")
    response.delete_cookie("user_name")
    return response
