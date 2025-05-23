# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from .database import SessionLocal
from .scraper import update_product_price, update_cross_platform_comparison
import asyncio

# Initialize scheduler
scheduler = AsyncIOScheduler()
playwright_instance = None  # Will be set from main.py

def schedule_product_scraping(product_id: str):
    """Schedule periodic price scraping for a product"""
    job_id = f"scrape_price_{product_id}"
    
    # Remove existing job if it exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Schedule price scraping every hour
    scheduler.add_job(
        func=scrape_product_job,
        trigger=IntervalTrigger(hours=0.01),
        args=[product_id],
        id=job_id,
        replace_existing=True,
        max_instances=1
    )
    
    # Schedule comparison update every 6 hours
    comparison_job_id = f"compare_price_{product_id}"
    if scheduler.get_job(comparison_job_id):
        scheduler.remove_job(comparison_job_id)
    
    scheduler.add_job(
        func=compare_product_job,
        trigger=IntervalTrigger(hours=0.02),
        args=[product_id],
        id=comparison_job_id,
        replace_existing=True,
        max_instances=1
    )

async def scrape_product_job(product_id: str):
    """Job function to scrape product price"""
    db = SessionLocal()
    try:
        await update_product_price(product_id, db, playwright_instance)
    finally:
        db.close()

async def compare_product_job(product_id: str):
    """Job function to update cross-platform comparison"""
    db = SessionLocal()
    try:
        await update_cross_platform_comparison(product_id, db, playwright_instance)
    finally:
        db.close()

def remove_product_jobs(product_id: str):
    """Remove all scheduled jobs for a product"""
    job_ids = [
        f"scrape_price_{product_id}",
        f"compare_price_{product_id}"
    ]
    
    for job_id in job_ids:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

# Daily cleanup job to remove old price records (keep last 30 days)
@scheduler.scheduled_job(CronTrigger(hour=0, minute=0))
async def cleanup_old_records():
    """Clean up old price records"""
    from datetime import datetime, timedelta
    from models import PriceRecord
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        deleted_count = (
            db.query(PriceRecord)
            .filter(PriceRecord.timestamp < cutoff_date)
            .delete()
        )
        db.commit()
        print(f"Cleaned up {deleted_count} old price records")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        db.rollback()
    finally:
        db.close()

# Health check job to verify scheduler is running
@scheduler.scheduled_job(IntervalTrigger(minutes=30))
async def scheduler_health_check():
    """Periodic health check for scheduler"""
    print(f"Scheduler health check - Active jobs: {len(scheduler.get_jobs())}")

def get_scheduler_status():
    """Get current scheduler status"""
    return {
        "running": scheduler.running,
        "active_jobs": len(scheduler.get_jobs()),
        "jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in scheduler.get_jobs()
        ]
    }