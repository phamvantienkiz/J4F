from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_db, get_current_user
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token,
    UserPreferenceResponse, UserPreferenceUpdate
)
from backend.app.services import auth_service

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(db, user_in)
    access_token = auth_service.create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(login_in: UserLogin, db: AsyncSession = Depends(get_db)):
    access_token = await auth_service.authenticate_user(db, login_in)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/preference", response_model=UserPreferenceResponse)
async def get_preference(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pref = await auth_service.get_user_preference(db, current_user.id)
    return pref

@router.put("/preference", response_model=UserPreferenceResponse)
async def update_preference(
    pref_in: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pref = await auth_service.update_user_preference(db, current_user.id, pref_in)
    return pref
