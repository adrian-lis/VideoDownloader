@echo off
setlocal

if not exist ".venv\Scripts\python.exe" (
    echo The application is not installed yet.
    echo.
    echo Run install.bat first.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" downloader.py

if errorlevel 1 (
    echo.
    echo The application exited with an error.
    pause
)

endlocal
