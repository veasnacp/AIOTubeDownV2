@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo Starting Telegram Bot using uv...
    uv run bot.py
) else (
    echo Starting Telegram Bot using python...
    python bot.py
)
pause
