@echo off
title TimeLog
echo.
echo  ========================================
echo   TimeLog - Starting...
echo  ========================================
echo.

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python not found. Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if required packages are already importable
python -c "import flask, xlrd, xlwt, xlutils" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  Dependencies OK.
    goto start
)

REM Try to install if not present
echo  Installing dependencies (first run only)...
pip install Flask xlrd==1.2.0 xlwt xlutils >nul 2>&1

REM Check again after install attempt
python -c "import flask, xlrd, xlwt, xlutils" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Could not import required packages.
    echo  Please run manually: pip install Flask xlrd==1.2.0 xlwt xlutils
    pause
    exit /b 1
)

:start
echo  Starting TimeLog on http://localhost:5000
echo  Close this window to stop the server.
echo.

python app.py

pause
