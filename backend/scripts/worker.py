"""Celery entry point. Long-running parsing, embedding and report tasks belong here."""
from celery import Celery
from app.core.config import get_settings

celery_app = Celery("supplymind", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.task_routes = {"supplymind.*": {"queue": "analysis"}}
