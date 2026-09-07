#!/bin/bash
echo "Video Man for Windows - Setup (PowerShell/Git Bash)"
echo ""

if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

PYTHON=python
if command -v python3 &> /dev/null; then PYTHON=python3; fi

echo "✅ Python found: $($PYTHON --version)"
$PYTHON -m pip install -r requirements.txt

if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ ffmpeg not found - please install: https://ffmpeg.org/"
else
    echo "✅ ffmpeg found"
fi

echo "✅ Done! Run: $PYTHON src/main.py"
