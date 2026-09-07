"""
Custom templates manager for Video Man.
"""
import json
from pathlib import Path
from typing import List, Dict

class TemplateManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def get_templates(self) -> List[Dict]:
        return self.settings.get("custom_templates", [])

    def add_template(self, name: str, command: str):
        templates = self.get_templates()
        templates.append({"name": name, "command": command})
        self.settings.set("custom_templates", templates)

    def remove_template(self, index: int):
        templates = self.get_templates()
        if 0 <= index < len(templates):
            templates.pop(index)
            self.settings.set("custom_templates", templates)

    def update_template(self, index: int, name: str, command: str):
        templates = self.get_templates()
        if 0 <= index < len(templates):
            templates[index] = {"name": name, "command": command}
            self.settings.set("custom_templates", templates)
