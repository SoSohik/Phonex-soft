@echo off
chcp 65001 > nul
title PHONEX SOFT - Telegram Login Tool
echo Starting PHONEX Telegram System Login...
py -3 login.py
if %errorlevel% neq 0 (
    python login.py
)
if %errorlevel% neq 0 (
    echo.
    echo Make sure Python and dependencies are installed!
    pause
)
