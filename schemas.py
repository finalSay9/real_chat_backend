from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from enum import Enum as PyEnum 
import re
from enum import StrEnum





class Base(BaseModel):
    username: str
    fullname: str | None = None
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",          
    )


    @field_validator('username')
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", value):
            raise ValueError("Username must be 3-20 characters long and contain only letters, numbers, or underscores")
        return value
    
   

class CreateUser(Base):
    password: str


class UserResponse(Base):
    id: int


    class Config:
        from_attributes = True




class Token(BaseModel):
    access_token: str
    token_type: str



class TokenData(BaseModel):
    username: str | None = None



