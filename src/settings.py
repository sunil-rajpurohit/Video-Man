"""
Video Man settings persistence.
"""
import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_SETTINGS = {
    "download_dir": str(Path.home() / "Downloads" / "Video Man"),
    "theme": "dark",  # dark, light, system
    "dynamic_color": True,
    "use_aria2c": False,
    "aria2c_path": "aria2c",
    "ffmpeg_path": "ffmpeg",
    "audio_format": "mp3",  # mp3, m4a, opus, flac, wav
    "audio_quality": "0",
    "video_height": "best",  # best, 2160, 1440, 1080, 720, 480
    "embed_thumbnail": True,
    "embed_metadata": True,
    "embed_subtitles": False,
    "auto_subs": False,
    "sub_langs": ["en"],
    "download_playlist": False,
    "sponsorblock": False,
    "embed_chapters": True,
    "output_template": "%(title)s [%(id)s].%(ext)s",
    "max_concurrent": 3,
    "cookies_browser": "",  # chrome, firefox, edge
    "custom_templates": [
        {
            "name": "Best Video + Best Audio (1080p max)",
            "command": '-f "bv*[height<=1080]+ba/b" --embed-thumbnail --embed-metadata {url}'
        },
        {
            "name": "Audio Only MP3 + Thumbnail",
            "command": '-x --audio-format mp3 --embed-thumbnail --embed-metadata {url}'
        },
        {
            "name": "Fast with aria2c",
            "command": '--external-downloader aria2c --external-downloader-args "-x 16 -k 1M" {url}'
        }
    ]
}

class SettingsManager:
    def __init__(self):
        self.config_dir = Path.home() / ".video-man"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self.settings = self.load()

    def load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge with defaults for new keys
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(data)
                    return merged
            except:
                return DEFAULT_SETTINGS.copy()
        return DEFAULT_SETTINGS.copy()

    def save(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]):
        self.settings.update(updates)
        self.save()
