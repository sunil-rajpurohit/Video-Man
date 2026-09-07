import PyInstaller.__main__
import os

# Build Video Man for Windows EXE
# Run: python build.py

PyInstaller.__main__.run([
    'src/main.py',
    '--name=Video-Man',
    '--windowed',  # no console
    '--onefile',
    '--icon=assets/Icon_OG.png',
    '--add-data=assets;assets',
    '--hidden-import=yt_dlp',
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--hidden-import=mutagen',
    '--collect-all=yt_dlp',
    '--collect-all=customtkinter',
    '--noconfirm',
    '--clean',
])
