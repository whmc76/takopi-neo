@echo off
setlocal

cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo [takopi] Missing "uv" on PATH.
    echo [takopi] Install it first: https://docs.astral.sh/uv/getting-started/installation/
    echo.
    pause
    exit /b 1
)

uv python find 3.14 >nul 2>nul
if errorlevel 1 (
    echo [takopi] Python 3.14 was not found. Installing it with uv...
    call uv python install 3.14
    if errorlevel 1 (
        echo.
        echo [takopi] Failed to install Python 3.14.
        pause
        exit /b 1
    )
)

echo [takopi] Starting in "%CD%"
call uv run --python 3.14 takopi %*
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
    echo.
    echo [takopi] Exited with code %exit_code%.
    pause
)

exit /b %exit_code%
