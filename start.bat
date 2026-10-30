@echo off
chcp 65001 > nul
title PHONEX SOFT v1.0
echo Starting PHONEX SOFT v1.0...
py -3 main.py
if %errorlevel% neq 0 (
    python main.py
)
if %errorlevel% neq 0 (
    echo.
    echo Make sure Python and dependencies are installed:
    echo pip install -r requirements.txt
    pause
)
