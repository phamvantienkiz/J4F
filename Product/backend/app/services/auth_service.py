from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from backend.app.models.user import User
from backend.app.models.preference import UserPreference
from backend.app.core.security import get_password_hash, verify_password, create_access_token
from backend.app.schemas.user import UserCreate, UserLogin, UserPreferenceUpdate

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # Create User
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        store_name=user_in.store_name
    )
    db.add(user)
    await db.flush()

    # Create Default User Preferences
    pref = UserPreference(
        user_id=user.id,
        preferred_market="US",
        target_margin=40.0,
        max_shipping_days=7,
        fulfillment_priority="margin"
    )
    db.add(pref)
    
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, login_in: UserLogin) -> str:
    result = await db.execute(select(User).where(User.email == login_in.email))
    user = result.scalars().first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
    
    # Create token
    return create_access_token(user.id)

async def get_user_preference(db: AsyncSession, user_id: str) -> UserPreference:
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    pref = result.scalars().first()
    if not pref:
        # Fallback create default
        pref = UserPreference(
            user_id=user_id,
            preferred_market="US",
            target_margin=40.0,
            max_shipping_days=7,
            fulfillment_priority="margin"
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref

async def update_user_preference(db: AsyncSession, user_id: str, pref_in: UserPreferenceUpdate) -> UserPreference:
    pref = await get_user_preference(db, user_id)
    
    update_data = pref_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)
        
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref
