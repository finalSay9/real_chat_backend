from fastapi import APIRouter, HTTPException, status, Depends
from schemas import CreateUser, UserResponse
from sqlalchemy.orm import Session
from dependency import get_db
from models import User
from security import hash_password
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, UserStatus
from schemas import UserPublic, UserUpdate, StatusUpdate
from auth import get_current_user
from ws_manager import manager


router = APIRouter(
    prefix='/users',
    tags=['users']
)


@router.post('/create', status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user(user: CreateUser, db: Session=Depends(get_db)):
    #check if username already exist
    exsting_username=db.query(User).filter(User.username == user.username).first()
    if exsting_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already exist")
    print("Password length:", len(user.password))
    new_user = User(
        username=user.username,
        fullname=user.fullname,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/status", response_model=UserPublic)
async def update_status(
    body: StatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.status = body.status
    await db.commit()
    await db.refresh(current_user)

    # Notify all connected clients about status change
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
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

