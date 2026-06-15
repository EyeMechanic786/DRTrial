@echo off
cd /d %~dp0..
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt -q
set PYTHONPATH=.
uvicorn apps.api.main:app --reload --port 8000
