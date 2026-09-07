"""
Simple batch installer for Windows dependencies
"""
@echo off
echo Video Man for Windows - Setup
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10+ from python.org
    echo    Make sure to check "Add to PATH"
    pause
    exit /b
)

echo ✅ Python found
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Check ffmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ ffmpeg not found. Installing via winget...
    winget install Gyan.FFmpeg -e
    if errorlevel 1 (
        echo ❌ Could not install ffmpeg automatically.
        echo    Please install manually: https://ffmpeg.org/download.html
        echo    And add to PATH
    )
) else (
    echo ✅ ffmpeg found
)

REM Check aria2c optional
aria2c --version >nul 2>&1
if errorlevel 1 (
    echo ℹ️ aria2c not found (optional, for faster downloads)
    echo    Install via: winget install aria2.aria2
) else (
    echo ✅ aria2c found
)

echo.
echo ✅ Setup complete! Run with: python src/main.py
echo    Or build EXE: python build.py
pause
