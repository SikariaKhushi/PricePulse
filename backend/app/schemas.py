# schemas.py
from pydantic import BaseModel, HttpUrl, EmailStr, validator
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    date_registered: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Product Schemas
class ProductTrack(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_url(cls, v):
        url_str = str(v)
        supported_platforms = ['amazon.in', 'flipkart.com', 'meesho.com']
        if not any(platform in url_str for platform in supported_platforms):
            raise ValueError('URL must be from supported platforms: Amazon, Flipkart, or Meesho')
        return v

class ProductResponse(BaseModel):
    product_id: str
    name: str
    image_url: str
    platform: str
    current_price: int
    url: str
    
    class Config:
        from_attributes = True

# Price History Schema
class PriceHistoryResponse(BaseModel):
    timestamp: datetime
    price: int
    
    class Config:
        from_attributes = True

# Comparison Schema
class ComparisonResponse(BaseModel):
    platform: str
    price: int
    url: str
    
    class Config:
        from_attributes = True

# Alert Schemas
class AlertCreate(BaseModel):
    product_id: str
    target_price: int
    
    @validator('target_price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Target price must be greater than 0')
        return v

class AlertCreateResponse(BaseModel):
    alert_id: str
    status: str

class AlertResponse(BaseModel):
    alert_id: str
    product_id: str
    email: str
    target_price: int
    is_active: bool
    is_triggered: bool
    date_created: datetime
    date_triggered: Optional[datetime] = None
    
    class Config:
        from_attributes = True