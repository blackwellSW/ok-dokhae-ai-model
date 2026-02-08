
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    user_type: str = "student"
    is_active: bool = True
    is_verified: bool = False
    profile_data: Dict = {}

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_data: Optional[Dict] = None

class UserInDB(UserBase):
    user_id: str
    hashed_password: str
    created_at: str
    updated_at: str

class User(UserInDB):
    pass
