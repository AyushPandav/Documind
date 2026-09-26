import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.auth.neon_users import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_last_login
)
from app.config import settings

logger = logging.getLogger("DocuMind.AuthRouter")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    full_name: Optional[str] = Field("", description="Full display name")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


from typing import Optional, Dict, Any, Union

class UserResponse(BaseModel):
    id: Union[str, int]
    email: str
    full_name: str
    is_active: bool
    role: str
    created_at: Optional[Any] = None
    source: Optional[str] = "neondb"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Auth Dependencies ────────────────────────────────────────────────────────
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Strict dependency: extracts and verifies the JWT token.
    Raises HTTP 401 if missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = await get_user_by_id(user_id)
    if not user:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    return user


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    Permissive dependency: returns user dict if valid token provided, else None.
    Allows guest queries while enriching responses for logged-in users.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await get_user_by_id(user_id)
    except Exception:
        return None


# ─── Auth Endpoints ───────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest):
    """
    Registers a new user on NeonDB (with local SQLite fallback).
    Hashes password via bcrypt and returns JWT access and refresh tokens.
    """
    clean_email = req.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=400, detail="Invalid email format.")

    logger.info(f"[Auth] Register request for: '{clean_email}'")

    existing_user = await get_user_by_email(clean_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{clean_email}' already exists."
        )

    hashed_pw = hash_password(req.password)
    user = await create_user(
        email=clean_email,
        full_name=req.full_name or clean_email.split("@")[0],
        hashed_pw=hashed_pw,
        role="user"
    )

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user account.")

    # Generate JWT tokens
    user_id = user["id"]
    access_token = create_access_token({"sub": str(user_id), "email": clean_email, "role": user.get("role", "user")})
    refresh_token = create_refresh_token({"sub": str(user_id), "email": clean_email})

    user_resp = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        is_active=bool(user.get("is_active", True)),
        role=user.get("role", "user"),
        created_at=str(user.get("created_at", "")),
        source=user.get("source", "neondb")
    )

    logger.info(f"[Auth] ✅ User registered successfully: '{clean_email}' (Source: {user.get('source')})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_resp
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest):
    """
    Authenticates user credentials against NeonDB.
    Returns new access and refresh tokens on success.
    """
    clean_email = req.email.strip().lower()
    logger.info(f"[Auth] Login attempt for: '{clean_email}'")

    user = await get_user_by_email(clean_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stored_hash = user.get("hashed_password") or user.get("hashed_pw", "")
    if not verify_password(req.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    # Update last login timestamp in background
    await update_last_login(user["id"])

    user_id = user["id"]
    access_token = create_access_token({"sub": str(user_id), "email": clean_email, "role": user.get("role", "user")})
    refresh_token = create_refresh_token({"sub": str(user_id), "email": clean_email})

    user_resp = UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        is_active=bool(user.get("is_active", True)),
        role=user.get("role", "user"),
        created_at=str(user.get("created_at", "")),
        source=user.get("source", "neondb")
    )

    logger.info(f"[Auth] ✅ User logged in: '{clean_email}' (ID: {user_id})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_resp
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(req: RefreshTokenRequest):
    """
    Generates a new access token using a valid refresh token.
    """
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Malformed token subject.")

    user = await get_user_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    new_access_token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user.get("role", "user")
    })

    return TokenRefreshResponse(access_token=new_access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the profile and status of the currently authenticated user.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        is_active=bool(current_user.get("is_active", True)),
        role=current_user.get("role", "user"),
        created_at=str(current_user.get("created_at", "")),
        source=current_user.get("source", "neondb")
    )


@router.get("/status")
async def auth_system_status():
    """
    Returns the current operational status of the authentication system.
    """
    neon_configured = bool(settings.NEON_DATABASE_URL)
    return {
        "status": "online",
        "provider": "NeonDB Serverless PostgreSQL" if neon_configured else "Local SQLite (offline)",
        "cloud_sync_enabled": settings.ENABLE_CLOUD_SYNC,
        "token_algorithm": settings.JWT_ALGORITHM,
        "access_token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "offline_fallback_active": True
    }
