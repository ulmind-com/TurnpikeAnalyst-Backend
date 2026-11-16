from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from app.db.mongodb import get_db
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.crud.user import get_users, create_user, update_user, delete_user, get_user_by_email
from app.api.deps import get_current_active_user, require_roles
from app.models.enums import UserRole

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))):
    users = await get_users(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(user_in: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))):
    # Optional role check: require_roles([UserRole.ADMIN])
    user_exists = await get_user_by_email(db, user_in.email)
    if user_exists:
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")
    user = await create_user(db, user_in)
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_existing_user(user_id: str, user_in: UserUpdate, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))):
    user = await update_user(db, user_id, user_in)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_user: dict = Depends(require_roles([UserRole.ADMIN.value]))):
    success = await delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None
