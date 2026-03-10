from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dependency import get_db
from models import User
from schemas import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserPublic, UserUpdate, StatusUpdate
    )
from security import (
    create_access_token, hash_password, verify_password,
    get_current_user, get_current_user_async
)
from ws_manager import manager


router = APIRouter(prefix="/users", tags=["users"])


# ─── Auth routes ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        select(User).where(User.username == body.username)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=body.username,
        display_name=body.display_name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# tokenUrl in OAuth2PasswordBearer points here — path MUST match exactly
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.username == body.username)
    ).scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ─── User routes ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/status", response_model=UserPublic)
async def update_status(
    body: StatusUpdate,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_db),
):
    current_user.status = body.status
    await db.commit()
    await db.refresh(current_user)

    await manager.broadcast_all(
        {
            "type": "status_change",
            "data": {"user_id": current_user.id, "status": body.status},
        },
        exclude=current_user.id,
    )
    return current_user


@router.get("", response_model=list[UserPublic])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_async),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user