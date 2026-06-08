from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.services.price_monitor import PriceMonitorService


scheduler = BackgroundScheduler(timezone="UTC")


def run_price_alert_check() -> None:
    db = SessionLocal()
    try:
        PriceMonitorService(db).check_price_alerts()
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(run_price_alert_check, "interval", minutes=60, id="price_alerts", replace_existing=True)
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
