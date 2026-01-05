"""
Background Task Scheduler for Retention Jobs.

Uses APScheduler for reliable scheduled task execution.
Law 25 Compliance: Automated data retention enforcement.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from repositories.database import SessionLocal


# Global scheduler instance
scheduler: BackgroundScheduler | None = None


def retention_cleanup_job() -> None:
    """
    Scheduled job to run retention cleanup.

    Creates its own database session for isolation.
    """
    from services.retention_service import RetentionService

    logger.info("Running scheduled retention cleanup job")

    db = SessionLocal()
    try:
        results = RetentionService.run_all_cleanup_jobs(db)
        logger.info(f"Retention cleanup completed: {results}")
    except Exception as e:
        logger.error(f"Retention cleanup failed: {e}")
        raise
    finally:
        db.close()


def setup_scheduler() -> None:
    """
    Configure and start the background scheduler.

    Schedules:
    - Retention cleanup: Daily at 2:00 AM
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return

    scheduler = BackgroundScheduler()

    # Add retention cleanup job - runs daily at 2 AM
    scheduler.add_job(
        retention_cleanup_job,
        CronTrigger(hour=2, minute=0),
        id="retention_cleanup",
        name="Data Retention Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace for missed jobs
    )

    # Start scheduler
    scheduler.start()
    logger.info("Background scheduler started with retention cleanup job at 2:00 AM")


def shutdown_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")
        scheduler = None


def get_scheduler_status() -> dict:
    """Get current scheduler status for monitoring."""
    global scheduler

    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
            }
        )

    return {"running": scheduler.running, "jobs": jobs}


def trigger_retention_cleanup_now() -> dict:
    """
    Manually trigger retention cleanup (for admin use).

    Returns:
        Results of the cleanup operation
    """
    from services.retention_service import RetentionService

    logger.info("Manual retention cleanup triggered")

    db = SessionLocal()
    try:
        results = RetentionService.run_all_cleanup_jobs(db)
        logger.info(f"Manual retention cleanup completed: {results}")
        return results
    finally:
        db.close()
