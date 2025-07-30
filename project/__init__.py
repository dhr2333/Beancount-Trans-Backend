# project/__init__.py
from project.celery import app as celery_app

__all__ = ['celery_app']