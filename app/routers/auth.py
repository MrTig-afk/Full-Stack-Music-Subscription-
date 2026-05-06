"""Authentication routes: login, register, and logout.

Provides user authentication endpoints that manage credentials in the DynamoDB
login table. Uses plaintext passwords for demo purposes (use bcrypt/JWT in production).

Endpoints:
  - POST /login — Authenticate user with email and password
  - POST /register — Create new user account
  - GET /logout — Logout endpoint (GET variant for browsers)
  - POST /logout — Logout endpoint (POST variant)
  - DELETE /logout — Logout endpoint (DELETE variant)

Notes:
  - All endpoints use the login_table from DynamoDB
  - Passwords are stored plaintext (demo only; use hashing in production)
  - Cookies are set but not used by frontend (sessionStorage used instead)
  - All endpoints log authentication attempts for debugging
"""

from fastapi import APIRouter, HTTPException
from fastapi.logger import logger
from fastapi.responses import JSONResponse

from app.db import login_table
from app.schemas import LoginRequest, RegisterRequest

router = APIRouter()


@router.post("/login")
def login_user(payload: LoginRequest):
    """Authenticate user with email and password.
    
    Queries the login table for the user by email.
    Verifies password matches stored value.
    On success, returns user_name and email.
    On failure, returns 401 Unauthorized.
    
    Args:
        payload: LoginRequest with email and password
        
    Returns:
        JSONResponse with message, user_name, email on success
        
    Raises:
        HTTPException: 401 if email not found or password incorrect
        
    Example:
        POST /login
        {"email": "user@example.com", "password": "pass123"}
    """
    logger.debug("Login attempt for email=%s", payload.email)
    result = login_table.get_item(Key={"email": payload.email})
    user = result.get("Item")

    if not user or user.get("password") != payload.password:
        logger.debug("Login failed for email=%s", payload.email)
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
    logger.debug("Login successful for email=%s", user_email)
    return response


@router.post("/register")
def register_user(payload: RegisterRequest):
    """Register a new user account.
    
    Checks if email already exists in the login table.
    If not, creates new user with email, user_name, and password.
    On success, returns 200 OK.
    On failure (email exists), returns 400 Bad Request.
    
    Args:
        payload: RegisterRequest with email, user_name, and password
        
    Returns:
        dict with message on success
        
    Raises:
        HTTPException: 400 if email already exists
        
    Example:
        POST /register
        {"email": "newuser@example.com", "user_name": "John", "password": "pass123"}
    """
    logger.debug("Register attempt for email=%s", payload.email)
    result = login_table.get_item(Key={"email": payload.email})

    if "Item" in result:
        logger.debug("Register failed because email already exists: %s", payload.email)
        raise HTTPException(status_code=400, detail="The email already exists")

    login_table.put_item(
        Item={
            "email": payload.email,
            "user_name": payload.user_name,
            "password": payload.password,
        }
    )

    logger.debug("Register successful for email=%s", payload.email)
    return {"message": "Registered successfully"}


@router.get("/logout")
def logout_user():
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("user_email")
    response.delete_cookie("user_name")
    logger.debug("Logout requested")
    return response


@router.post("/logout")
def logout_user_post():
    return logout_user()


@router.delete("/logout")
def logout_user_delete():
    return logout_user()
