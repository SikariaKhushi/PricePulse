# models.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    date_registered = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    
    product_id = Column(String, primary_key=True, default=generate_uuid)
    platform = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    image_url = Column(String)
    brand = Column(String)
    model = Column(String)
    current_price = Column(Integer, nullable=False)  # Store in cents/paise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_records = relationship("PriceRecord", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")
    comparisons = relationship("PlatformComparison", back_populates="product", cascade="all, delete-orphan")

class PriceRecord(Base):
    __tablename__ = "price_records"
    
    record_id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)
    price = Column(Integer, nullable=False)  # Store in cents/paise
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform = Column(String, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="price_records")

class Alert(Base):
    __tablename__ = "alerts"
    
    alert_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)
    target_price = Column(Integer, nullable=False)  # Store in cents/paise
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_triggered = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    product = relationship("Product", back_populates="alerts")

class PlatformComparison(Base):
    __tablename__ = "platform_comparisons"
    
    comparison_id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)
    platform = Column(String, nullable=False)
    found_name = Column(String)
    found_price = Column(Integer)  # Store in cents/paise
    found_url = Column(String)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="comparisons")