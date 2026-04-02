import os

from celery import Celery
from celery.schedules import crontab

from app.db import SessionLocal
from app.models import User
from app.services import crud

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_url, backend=redis_url)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute=0, hour="*"),
        update_all_user_taste_vectors.s(),
    )


@celery_app.task
def update_all_user_taste_vectors():
    """Refresh cached taste vectors hourly so API reads stay fast."""
    db = SessionLocal()
    try:
        user_ids = [user.id for user in db.query(User.id).all()]
        for user_id in user_ids:
            crud.refresh_user_taste_vector(db, user_id)
        return {"updated_users": len(user_ids)}
    finally:
        db.close()
