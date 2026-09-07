"""
Utilities - ffmpeg check, aria2c, clipboard etc
"""
import shutil
import subprocess
import sys
from pathlib import Path

def check_ffmpeg(ffmpeg_path="ffmpeg") -> bool:
    try:
        result = subprocess.run([ffmpeg_path, "-version"], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return shutil.which(ffmpeg_path) is not None

def check_aria2c(aria2c_path="aria2c") -> bool:
    try:
        result = subprocess.run([aria2c_path, "--version"], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return shutil.which(aria2c_path) is not None

def get_clipboard_text():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except:
        return ""

def is_valid_url(text: str) -> bool:
    text = text.strip()
    return text.startswith("http://") or text.startswith("https://")

def format_bytes(num_bytes):
    if not num_bytes:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"

def format_speed(speed):
    if not speed:
        return ""
    return f"{format_bytes(speed)}/s"

def get_download_folder():
    return str(Path.home() / "Downloads" / "Video Man")
