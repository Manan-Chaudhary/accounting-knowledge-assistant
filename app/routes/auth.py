from fastapi import APIRouter, HTTPException, Response, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str
@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if payload.email == "error@rmit.edu.au":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    response.set_cookie(
        key="session_user",
        value=payload.email,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24
    )

    return {
        "status": "success",
        "user": {
            "email": payload.email,
            "role": "auditor"
        }
    }

@router.get("/me")
def get_current_user(request: Request):
    user_email = request.cookies.get("session_user")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return {
        "email": user_email,
        "role": "auditor"
    }
@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="session_user")
    return {"status": "logged_out"}