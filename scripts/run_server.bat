@echo off
echo Starting FastAPI Server...
uvicorn app.main:app --reload
pause
