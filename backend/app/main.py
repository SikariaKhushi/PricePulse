# main.py
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, APIRouter, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright
import asyncio
import sys
from typing import List, Optional, Any
import uvicorn

from .database import get_db, init_db
from .models import *
from .schemas import *
from .scraper import ProductScraper, update_cross_platform_comparison
from .scheduler import scheduler, schedule_product_scraping, set_playwright_instance, get_scheduler_status
from .auth import get_current_user, create_access_token, verify_password, get_password_hash
from .email_service import send_price_drop_alert

app = FastAPI(
    title="PricePulse API",
    description="Price tracking and comparison API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    scheduler.start()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    app.state.playwright = await async_playwright().start()
    set_playwright_instance(app.state.playwright)

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    await app.state.playwright.stop()

# User Authentication Endpoints
@app.post("/users/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        user_id=db_user.user_id,
        email=db_user.email,
        name=db_user.name,
        date_registered=db_user.date_registered
    )

@app.post("/users/login", response_model=TokenResponse)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(data={"sub": db_user.email})
    return TokenResponse(access_token=access_token, token_type="bearer")

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        date_registered=current_user.date_registered
    )

@app.put("/users/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.name:
        current_user.name = user_update.name
    if user_update.password:
        current_user.password_hash = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        date_registered=current_user.date_registered
    )

@app.delete("/users/me", status_code=204)
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(current_user)
    db.commit()

# Product Endpoints
@app.post("/products/track", response_model=ProductResponse)
async def track_product(
    product_data: ProductTrack,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Check if product already exists
    existing_product = db.query(Product).filter(Product.url == str(product_data.url)).first()
    if existing_product:
        raise HTTPException(
            status_code=409,
            detail="Product already being tracked"
        )

    # 2. Scrape initial product data
    try:
        async with ProductScraper(request.app.state.playwright) as scraper:
            product_info = await scraper.scrape_product(str(product_data.url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to scrape product: {str(e)}")

    # 3. Create product record
    db_product = Product(
        platform=product_info["platform"],
        url=str(product_data.url),
        name=product_info["name"],
        image_url=product_info["image_url"],
        brand=product_info.get("brand", ""),
        model=product_info.get("model", ""),
        current_price=product_info["price"]
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # 4. Add initial price record
    price_record = PriceRecord(
        product_id=db_product.product_id,
        price=product_info["price"],
        platform=product_info["platform"]
    )
    db.add(price_record)
    db.commit()

    # 5. Schedule periodic scraping (price + comparison)
    schedule_product_scraping(db_product.product_id)

    # 6. Trigger cross-platform comparison in background (fast response for user)
    background_tasks.add_task(
        trigger_initial_comparison,
        db_product.product_id,
        request.app.state.playwright
    )

    # 7. Return product info
    return ProductResponse(
        product_id=db_product.product_id,
        name=db_product.name,
        image_url=db_product.image_url,
        platform=db_product.platform,
        current_price=db_product.current_price,
        url=db_product.url
    )

# Helper for background comparison
async def trigger_initial_comparison(product_id: str, playwright: Any):
    db = get_db().__next__()  # Get a new DB session for the background task
    try:
        async with ProductScraper(playwright) as scraper:
            await update_cross_platform_comparison(product_id, db, scraper)
    except Exception as e:
        print(f"[Comparison] Error updating comparison for product {product_id}: {str(e)}")
    finally:
        db.close()

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(
        product_id=product.product_id,
        name=product.name,
        image_url=product.image_url,
        platform=product.platform,
        current_price=product.current_price,
        url=product.url
    )

@app.get("/products", response_model=List[ProductResponse])
async def list_products(
    limit: int = 25,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(Product).offset(offset).limit(limit).all()
    return [
        ProductResponse(
            product_id=p.product_id,
            name=p.name,
            image_url=p.image_url,
            platform=p.platform,
            current_price=p.current_price,
            url=p.url
        ) for p in products
    ]

@app.get("/products/{product_id}/history", response_model=List[PriceHistoryResponse])
async def get_price_history(
    product_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price_records = (
        db.query(PriceRecord)
        .filter(PriceRecord.product_id == product_id)
        .order_by(PriceRecord.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [
        PriceHistoryResponse(timestamp=record.timestamp, price=record.price)
        for record in price_records
    ]

@app.get("/products/{product_id}/comparison", response_model=List[ComparisonResponse])
async def get_price_comparison(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get platform comparisons
    comparisons = (
        db.query(PlatformComparison)
        .filter(PlatformComparison.product_id == product_id)
        .all()
    )
    
    if not comparisons:
        raise HTTPException(
            status_code=502,
            detail="Price comparison data not available"
        )
    
    return [
        ComparisonResponse(
            platform=comp.platform,
            price=comp.found_price,
            url=comp.found_url
        ) for comp in comparisons
    ]

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Check if product exists
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Remove associated price records and alerts (optional but recommended)
    db.query(PriceRecord).filter(PriceRecord.product_id == product_id).delete()
    db.query(Alert).filter(Alert.product_id == product_id).delete()
    db.query(PlatformComparison).filter(PlatformComparison.product_id == product_id).delete()

    # 3. Remove the product itself
    db.delete(product)
    db.commit()

    # 4. Remove scheduled jobs for this product
    from .scheduler import remove_product_jobs
    remove_product_jobs(product_id)

    # 5. No response body needed for 204
    return

# Alert Endpoints
@app.post("/alerts/", response_model=AlertCreateResponse)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(Product).filter(Product.product_id == alert_data.product_id).first()
    if not product:
        raise HTTPException(status_code=400, detail="Product not found")
    
    # Check if alert already exists
    existing_alert = (
        db.query(Alert)
        .filter(
            Alert.user_id == current_user.user_id,
            Alert.product_id == alert_data.product_id,
            Alert.target_price == alert_data.target_price
        )
        .first()
    )
    if existing_alert:
        raise HTTPException(status_code=409, detail="Alert already exists")
    
    # Create alert
    db_alert = Alert(
        user_id=current_user.user_id,
        product_id=alert_data.product_id,
        target_price=alert_data.target_price
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    
    return AlertCreateResponse(
        alert_id=db_alert.alert_id,
        status="scheduled"
    )

@app.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id, Alert.user_id == current_user.user_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        alert_id=alert.alert_id,
        product_id=alert.product_id,
        email=current_user.email,
        target_price=alert.target_price,
        is_active=alert.is_active,
        is_triggered=alert.is_triggered,
        date_created=alert.date_created,
        date_triggered=alert.date_triggered
    )

@app.get("/products/{product_id}/alerts", response_model=List[AlertResponse])
async def list_product_alerts(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alerts = (
        db.query(Alert)
        .filter(
            Alert.product_id == product_id,
            Alert.user_id == current_user.user_id
        )
        .all()
    )
    
    return [
        AlertResponse(
            alert_id=alert.alert_id,
            product_id=alert.product_id,
            email=current_user.email,
            target_price=alert.target_price,
            is_active=alert.is_active,
            is_triggered=alert.is_triggered,
            date_created=alert.date_created,
            date_triggered=alert.date_triggered
        ) for alert in alerts
    ]

@app.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id, Alert.user_id == current_user.user_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()

# Scheduler Endpoints
@app.post("/scheduler/trigger/{product_id}")
async def trigger_manual_scrape(
    product_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Trigger background scraping task
    background_tasks.add_task(scrape_and_update_product, product_id, db)
    
    return {"status": "scrape_started"}

async def scrape_and_update_product(product_id: str, db: Session):
    """Background task to scrape and update product price"""
    from scraper import update_product_price
    await update_product_price(product_id, db)

# Error Endpoints
@app.get("/products/{product_id}/errors")
async def get_scraping_errors(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # This would typically come from a logging system
    # For now, return a mock response
    return [
        {"timestamp": "2024-05-22T07:00:00Z", "error": "Request blocked"},
        {"timestamp": "2024-05-21T21:00:00Z", "error": "Product unavailable"}
    ]
@app.get("/health/scheduler")
def scheduler_status():
    return get_scheduler_status()

@app.get("/")
def read_root():
    return {"message": "Welcome to PricePulse API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)