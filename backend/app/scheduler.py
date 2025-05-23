# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from .database import SessionLocal
from .scraper import update_product_price, update_cross_platform_comparison
import asyncio
import logging

# Logger setup
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()
_playwright = None  # Internal variable

def set_playwright_instance(instance):
    """Set Playwright instance from FastAPI app state"""
    global _playwright
    _playwright = instance

def schedule_product_scraping(product_id: str):
    """Schedule periodic price scraping and comparison for a product"""
    job_id = f"scrape_price_{product_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    scheduler.add_job(
        func=lambda: asyncio.create_task(scrape_product_job(product_id)),
        trigger=IntervalTrigger(hours=1),  # Adjust as needed
        id=job_id,
        replace_existing=True,
        max_instances=1
    )

    comparison_job_id = f"compare_price_{product_id}"
    if scheduler.get_job(comparison_job_id):
        scheduler.remove_job(comparison_job_id)

    scheduler.add_job(
        func=lambda: asyncio.create_task(compare_product_job(product_id)),
        trigger=IntervalTrigger(hours=6),
        id=comparison_job_id,
        replace_existing=True,
        max_instances=1
    )

async def scrape_product_job(product_id: str):
    """Scrape product price"""
    db = SessionLocal()
    try:
        await update_product_price(product_id, db, _playwright)
    except Exception as e:
        logger.error(f"Error scraping product {product_id}: {e}")
    finally:
        db.close()

async def compare_product_job(product_id: str):
    """Update cross-platform price comparison"""
    db = SessionLocal()
    try:
        await update_cross_platform_comparison(product_id, db, _playwright)
    except Exception as e:
        logger.error(f"Error comparing product {product_id}: {e}")
    finally:
        db.close()

def remove_product_jobs(product_id: str):
    """Remove all scheduled jobs for a product"""
    job_ids = [f"scrape_price_{product_id}", f"compare_price_{product_id}"]
    for job_id in job_ids:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

@scheduler.scheduled_job(CronTrigger(hour=0, minute=0))
async def cleanup_old_records():
    """Clean up price records older than 30 days"""
    from datetime import datetime, timedelta
    from .models import PriceRecord

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        deleted = db.query(PriceRecord).filter(PriceRecord.timestamp < cutoff).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old price records")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

@scheduler.scheduled_job(IntervalTrigger(minutes=30))
async def scheduler_health_check():
    """Scheduler health log"""
    logger.info(f"Scheduler health check - Active jobs: {len(scheduler.get_jobs())}")

def get_scheduler_status():
    """Return scheduler state"""
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
