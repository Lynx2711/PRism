from .celery import app as celery_app
__all__ = ('celery_app',)

#this makes sure that celery starts wheneveer django starts, otherwise the celery app doesnt initialize until something explicitly imports it