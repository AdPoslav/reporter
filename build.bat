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
echo  [1/4] Checking PyInstaller...
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

:: Install Pillow only if not already present
echo  [2/4] Checking Pillow...
pip show Pillow >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Pillow not found, installing...
    python -m pip install Pillow
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: Could not install Pillow.
        pause & exit /b 1
    )
) else (
    echo  Pillow already installed, skipping.
)

:: Generate icon
echo  [3/4] Generating reporter.ico...
python create_icon.py
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Could not generate reporter.ico.
    pause & exit /b 1
)

:: Build
echo  [4/4] Building Reporter.exe  ^(this takes ~1-2 minutes^)...
python -m PyInstaller reporter.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Build failed. See output above for details.
    pause & exit /b 1
)

:: Done
echo.
echo  Done!
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
