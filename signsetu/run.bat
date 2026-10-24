@echo off
REM Windows one-command start: double-click or run run.bat
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
pip install -q -r requirements.txt
python -m backend.server %*
