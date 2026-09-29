@echo off
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
if not exist .env copy ..\.env.example .env
echo Open http://localhost:8000
uvicorn main:app --reload
