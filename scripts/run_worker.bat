@echo off
echo Starting Celery Worker...
celery -A app.worker.celery_app worker --loglevel=info --pool=solo
pause
