@echo off
setlocal

cd /d "%~dp0"
set "UV_LINK_MODE=copy"
set "PYTHON_PATH="

where uv >nul 2>nul
if errorlevel 1 (
    echo [takopi] Missing "uv" on PATH.
    echo [takopi] Install it first: https://docs.astral.sh/uv/getting-started/installation/
    echo.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%I in (`py -3.14 -c "import sys; raise SystemExit(1) if sys.version_info[:2] != (3, 14) or sys.version_info.releaselevel != 'final' else print(sys.executable)" 2^>nul`) do (
    set "PYTHON_PATH=%%I"
    goto :python_found
)

for /f "usebackq delims=" %%I in (`uv python find 3.14 2^>nul`) do (
    set "PYTHON_PATH=%%I"
    goto :python_found
)

echo [takopi] Python 3.14 was not found.
echo [takopi] This project requires a stable Python 3.14 interpreter.
echo [takopi] Install it first, then rerun this script.
echo [takopi] Example: uv python install 3.14
echo.
pause
exit /b 1

:python_found
"%PYTHON_PATH%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) and sys.version_info.releaselevel == 'final' else 1)"
if errorlevel 1 (
    echo [takopi] Found a Python 3.14 interpreter, but it is a pre-release build.
    echo [takopi] This script only runs with a stable Python 3.14 release.
    echo [takopi] Please install a final Python 3.14 build and rerun.
    echo.
    pause
    exit /b 1
)

echo [takopi] Starting in "%CD%"
call uv run --python "%PYTHON_PATH%" takopi %*
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
    echo.
    echo [takopi] Exited with code %exit_code%.
    pause
)

exit /b %exit_code%
