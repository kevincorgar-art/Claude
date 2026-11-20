@echo off
cd /d "%~dp0"
pip install -r requirements.txt
python watch.py setup
pause
