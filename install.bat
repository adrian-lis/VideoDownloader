@echo off
setlocal
cd /d "%~dp0"
title Video Downloader - Installer

echo.
echo Video Downloader - Installer
echo ==================================
echo.

echo [1/4] Checking Python...

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    echo Download: https://www.python.org/downloads/
    goto :failed
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    python --version
    goto :failed
)

python --version

echo.
echo [2/4] Preparing environment...

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment.
        goto :failed
    )
)

echo OK: Virtual environment ready.

echo.
echo [3/4] Installing dependencies...

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Could not update pip.
    goto :failed
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    echo Check your internet connection and requirements.txt.
    goto :failed
)

echo OK: Dependencies installed.

echo.
echo [4/4] Checking FFmpeg...

if exist "%~dp0ffmpeg\ffmpeg.exe" (
    echo OK: Local FFmpeg found.
) else (
    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo WARNING: FFmpeg was not found.
        echo Some downloads may require FFmpeg.
        echo Install it or place ffmpeg.exe in the ffmpeg folder.
    ) else (
        echo OK: FFmpeg found in PATH.
    )
)

echo.
echo Installation completed.
echo Start the application using run.bat.
echo.
pause
endlocal
exit /b 0

:failed
echo.
echo Installation failed. Fix the error and try again.
echo.
pause
endlocal
exit /b 1