@echo off
title Reporter - Build EXE
echo.
echo  ================================================
echo   Reporter - Building standalone EXE
echo  ================================================
echo.

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python not found in PATH.
    pause & exit /b 1
)

:: Install PyInstaller only if not already present
echo  [1/3] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  PyInstaller not found, installing...
    python -m pip install pyinstaller --quiet
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: Could not install PyInstaller.
        pause & exit /b 1
    )
) else (
    echo  PyInstaller already installed, skipping.
)

:: Build
echo  [2/3] Building Reporter.exe  ^(this takes ~1-2 minutes^)...
python -m PyInstaller reporter.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Build failed. See output above for details.
    pause & exit /b 1
)

:: Done
echo.
echo  [3/3] Done!
echo.
echo  ================================================
echo   dist\Reporter.exe  is ready to share
echo  ================================================
echo.
echo  IMPORTANT — before sending to a colleague:
echo    1. Make sure YOUR data is backed up:
echo       Settings ^> Data Management ^> Download JSON
echo    2. The EXE stores each user's data in:
echo       %%APPDATA%%\Reporter\timelog.db
echo    3. Your current dev data stays in the local
echo       timelog.db file and is NOT affected.
echo.
pause
