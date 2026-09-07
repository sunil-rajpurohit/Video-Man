"""
Video Man - Main UI
Material Design 3 inspired UI using CustomTkinter
Video and audio downloader for Windows

Features:
- Single window
- Composable frames for each application page
- Dynamic theme
- Video/audio/custom, metadata, thumbnails, subtitles, playlists, and aria2c
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
import customtkinter as ctk
from tkinter import filedialog, messagebox, PhotoImage
from PIL import Image

# Local imports
from settings import SettingsManager
from downloader import VideoManDownloader
from templates import TemplateManager
from utils import check_ffmpeg, check_aria2c, get_clipboard_text, is_valid_url, format_bytes, format_speed

# Configure CustomTkinter - Material 3 style
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0b111a"
SIDEBAR = "#0d141e"
CARD = "#111a26"
INPUT = "#1a2535"
BORDER = "#263449"
TEXT = "#eef4ff"
MUTED = "#91a2bb"
ACCENT = "#1677f9"
ACCENT_HOVER = "#2d8cff"
SECONDARY = "#1b2737"

class VideoManApp:
    def __init__(self):
        self.settings_mgr = SettingsManager()
        self.template_mgr = TemplateManager(self.settings_mgr)
        
        self.root = ctk.CTk()
        self.root.title("Video Man — Video/Audio Downloader")
        self.root.geometry("1180x800")
        self.root.minsize(1000, 680)
        self.root.configure(fg_color=BG)
        
        # Load the bundled application icon in source and PyInstaller layouts.
        try:
            icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets" / "Icon_OG.png"
            self.app_icon = PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.app_icon)
        except:
            pass

        # State
        self.current_info: Optional[Dict] = None
        self.download_dir = Path(self.settings_mgr.get("download_dir"))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.downloader: Optional[VideoManDownloader] = None
        self.is_downloading = False
        self.playlist_entries = []
        self.playlist_tasks = {}

        self.setup_ui()
        self.check_dependencies()
        self.auto_paste_clipboard()

    def setup_ui(self):
        # Root layout - sidebar + main
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ===== SIDEBAR =====
        self.sidebar = ctk.CTkFrame(self.root, width=210, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(28, 34), padx=18, fill="x")
        
        ctk.CTkLabel(logo_frame, text=">", width=42, height=42, corner_radius=12,
                 fg_color=ACCENT, text_color="white", font=("Segoe UI", 22, "bold")).pack(side="left")
        brand = ctk.CTkFrame(logo_frame, fg_color="transparent")
        brand.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(brand, text="Video Man", font=("Segoe UI", 22, "bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(brand, text="Video & Audio Downloader", font=("Segoe UI", 9), text_color=MUTED).pack(anchor="w")

        # Nav buttons
        self.nav_buttons = {}
        nav_items = [
            ("🏠  Home", "home"),
            ("📃  Playlist", "playlist"),
            ("📥  Downloads", "downloads"),
            ("⚙️  Settings", "settings"),
            ("📜  Templates", "templates"),
            ("ℹ️  About", "about"),
        ]
        for label, key in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=label, anchor="w", 
                               fg_color="transparent", hover_color=SECONDARY,
                               text_color=MUTED, font=("Segoe UI", 13), height=42, corner_radius=8)
            btn.pack(pady=2, padx=12, fill="x")
            btn.configure(command=lambda k=key: self.switch_page(k))
            self.nav_buttons[key] = btn

        # Active indicator
        self.set_active_nav("home")

        # Bottom sidebar - ffmpeg status
        self.ffmpeg_status_label = ctk.CTkLabel(self.sidebar, text="", font=("Segoe UI", 10), text_color="#888")
        self.ffmpeg_status_label.pack(side="bottom", pady=12, padx=12)

        # ===== MAIN CONTENT AREA =====
        self.main_frame = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Pages container
        self.pages = {}
        self.create_home_page()
        self.create_playlist_page()
        self.create_downloads_page()
        self.create_settings_page()
        self.create_templates_page()
        self.create_about_page()

        self.switch_page("home")

    def set_active_nav(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#174b91", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=MUTED)

    def switch_page(self, page_key):
        self.set_active_nav(page_key)
        for key, frame in self.pages.items():
            if key == page_key:
                frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            else:
                frame.grid_forget()

    # ===== HOME PAGE =====
    def create_home_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["home"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        # URL Input Card - Material 3 card style
        url_card = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        url_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        url_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_card, text="Enter URL", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(16,8))

        input_row = ctk.CTkFrame(url_card, fg_color="transparent")
        input_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,16))
        input_row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(input_row, placeholder_text="https://www.youtube.com/watch?v=...",
                                     height=44, font=("Segoe UI", 13), corner_radius=12,
                         fg_color=INPUT, border_color=BORDER, border_width=1)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.url_entry.bind("<Return>", lambda e: self.analyze_url())

        paste_btn = ctk.CTkButton(input_row, text="Paste", width=80, height=44, corner_radius=10,
                      command=self.paste_url, fg_color=SECONDARY, hover_color="#2b3b51")
        paste_btn.grid(row=0, column=1, padx=2)

        self.analyze_btn = ctk.CTkButton(input_row, text="Analyze", width=112, height=44, corner_radius=10,
                        command=self.analyze_url, font=("Segoe UI", 13, "bold"),
                        fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self.analyze_btn.grid(row=0, column=2, padx=(8,0))

        # Info card appears after analysis.
        self.info_card = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        # hidden initially
        self.info_card.grid_columnconfigure(1, weight=1)
        
        self.thumbnail_label = ctk.CTkLabel(self.info_card, text="No preview", width=160, height=90, fg_color=INPUT, corner_radius=8)
        self.thumbnail_label.grid(row=0, column=0, rowspan=3, padx=16, pady=16, sticky="n")

        self.title_label = ctk.CTkLabel(self.info_card, text="", font=("Segoe UI", 14, "bold"), wraplength=500, anchor="w", justify="left")
        self.title_label.grid(row=0, column=1, sticky="ew", padx=(0,16), pady=(16,2))

        self.uploader_label = ctk.CTkLabel(self.info_card, text="", font=("Segoe UI", 11), text_color="#888", anchor="w")
        self.uploader_label.grid(row=1, column=1, sticky="ew", padx=(0,16))

        self.duration_label = ctk.CTkLabel(self.info_card, text="", font=("Segoe UI", 11), text_color="#aaa", anchor="w")
        self.duration_label.grid(row=2, column=1, sticky="ew", padx=(0,16), pady=(0,16))

        # Download options.
        options_scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        options_scroll.grid(row=2, column=0, sticky="nsew", pady=(0,16))
        options_scroll.grid_columnconfigure(0, weight=1)

        options_card = ctk.CTkFrame(options_scroll, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        options_card.grid(row=0, column=0, sticky="ew")
        options_card.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(options_card, text="Download Options", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(16,12))

        # Mode segmented: Video / Audio / Custom.
        mode_frame = ctk.CTkFrame(options_card, fg_color=INPUT, corner_radius=12)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0,16))
        
        self.mode_var = ctk.StringVar(value="video")
        ctk.CTkRadioButton(mode_frame, text="🎬 Video", variable=self.mode_var, value="video", 
                          command=self.on_mode_change, font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)
        ctk.CTkRadioButton(mode_frame, text="🎵 Audio", variable=self.mode_var, value="audio",
                          command=self.on_mode_change, font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)
        ctk.CTkRadioButton(mode_frame, text="🛠️ Custom", variable=self.mode_var, value="custom",
                          command=self.on_mode_change, font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)

        # Video quality
        self.video_quality_label = ctk.CTkLabel(options_card, text="Quality", font=("Segoe UI", 12))
        self.video_quality_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0,4))
        self.video_quality_combo = ctk.CTkComboBox(options_card, values=["best", "2160 (4K)", "1440 (2K)", "1080", "720", "480", "360"],
                                                   width=200, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        self.video_quality_combo.grid(row=3, column=0, sticky="ew", padx=20, pady=(0,12))
        self.video_quality_combo.set("best")

        # Audio format
        self.audio_format_label = ctk.CTkLabel(options_card, text="Audio Format", font=("Segoe UI", 12))
        self.audio_format_label.grid(row=2, column=1, sticky="w", padx=20, pady=(0,4))
        self.audio_format_combo = ctk.CTkComboBox(options_card, values=["mp3", "m4a", "opus", "flac", "wav", "best"],
                                                  width=200, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        self.audio_format_combo.grid(row=3, column=1, sticky="ew", padx=20, pady=(0,12))
        self.audio_format_combo.set(self.settings_mgr.get("audio_format"))

        # Output folder
        self.folder_label = ctk.CTkLabel(options_card, text="Save to", font=("Segoe UI", 12))
        self.folder_label.grid(row=2, column=2, sticky="w", padx=20, pady=(0,4))
        folder_row = ctk.CTkFrame(options_card, fg_color="transparent")
        folder_row.grid(row=3, column=2, sticky="ew", padx=20, pady=(0,12))
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_entry = ctk.CTkEntry(folder_row, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        self.folder_entry.grid(row=0, column=0, sticky="ew")
        self.folder_entry.insert(0, str(self.download_dir))
        ctk.CTkButton(folder_row, text="📁", width=36, command=self.browse_folder, fg_color="#3a3a3a").grid(row=0, column=1, padx=(6,0))

        # Download feature toggles.
        toggles_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        toggles_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=20, pady=(0,8))

        self.embed_thumb_var = ctk.BooleanVar(value=self.settings_mgr.get("embed_thumbnail"))
        self.embed_meta_var = ctk.BooleanVar(value=self.settings_mgr.get("embed_metadata"))
        self.playlist_var = ctk.BooleanVar(value=self.settings_mgr.get("download_playlist"))
        self.subs_var = ctk.BooleanVar(value=self.settings_mgr.get("embed_subtitles"))
        self.aria2c_var = ctk.BooleanVar(value=self.settings_mgr.get("use_aria2c"))
        self.sponsorblock_var = ctk.BooleanVar(value=self.settings_mgr.get("sponsorblock"))

        ctk.CTkCheckBox(toggles_frame, text="Embed Thumbnail", variable=self.embed_thumb_var, font=("Segoe UI", 11)).pack(side="left", padx=(0,16), pady=4)
        ctk.CTkCheckBox(toggles_frame, text="Embed Metadata", variable=self.embed_meta_var, font=("Segoe UI", 11)).pack(side="left", padx=16, pady=4)
        ctk.CTkCheckBox(toggles_frame, text="Embed Subtitles", variable=self.subs_var, font=("Segoe UI", 11)).pack(side="left", padx=16, pady=4)
        ctk.CTkCheckBox(toggles_frame, text="Playlist", variable=self.playlist_var, font=("Segoe UI", 11)).pack(side="left", padx=16, pady=4)

        toggles_frame2 = ctk.CTkFrame(options_card, fg_color="transparent")
        toggles_frame2.grid(row=5, column=0, columnspan=3, sticky="ew", padx=20, pady=(0,16))
        ctk.CTkCheckBox(toggles_frame2, text="Use aria2c (faster)", variable=self.aria2c_var, font=("Segoe UI", 11)).pack(side="left", padx=(0,16), pady=4)
        ctk.CTkCheckBox(toggles_frame2, text="SponsorBlock", variable=self.sponsorblock_var, font=("Segoe UI", 11)).pack(side="left", padx=16, pady=4)

        # Custom template area
        self.custom_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.custom_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=(0,16))
        self.custom_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.custom_frame, text="Custom Command Template", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=(0,4))
        self.custom_combo = ctk.CTkComboBox(self.custom_frame, values=[t["name"] for t in self.template_mgr.get_templates()],
                                            width=300, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8,
                                            command=self.on_template_select)
        self.custom_combo.grid(row=1, column=0, sticky="ew", pady=(0,6))
        self.custom_entry = ctk.CTkEntry(self.custom_frame, placeholder_text='e.g., -f "bv*[height<=1080]+ba/b" --embed-metadata {url}',
                                         fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8, height=36)
        self.custom_entry.grid(row=2, column=0, sticky="ew")
        if self.template_mgr.get_templates():
            self.custom_entry.insert(0, self.template_mgr.get_templates()[0]["command"])

        self.on_mode_change()

        # Download button and progress.
        action_card = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        action_card.grid(row=3, column=0, sticky="ew")
        action_card.grid_columnconfigure(0, weight=1)

        progress_frame = ctk.CTkFrame(action_card, fg_color="transparent")
        progress_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=16)
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=8, corner_radius=4, progress_color=ACCENT, fg_color=INPUT)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0,8))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(progress_frame, text="Ready to download", font=("Segoe UI", 11), text_color="#888", anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w")

        self.speed_label = ctk.CTkLabel(progress_frame, text="", font=("Segoe UI", 11), text_color="#888", anchor="e")
        self.speed_label.grid(row=1, column=1, sticky="e")

        btn_frame = ctk.CTkFrame(action_card, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,16))
        btn_frame.grid_columnconfigure((0,1), weight=1)

        self.download_btn = ctk.CTkButton(btn_frame, text="Download", height=48, corner_radius=10,
                         font=("Segoe UI", 14, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.start_download)
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0,8))

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", height=48, corner_radius=10, width=120,
                           fg_color=SECONDARY, hover_color="#2b3b51",
                                       command=self.cancel_download, state="disabled")
        self.cancel_btn.grid(row=0, column=1, sticky="ew", padx=(8,0))

    def create_playlist_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["playlist"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(page, text="Playlist Downloader", font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 16))

        input_card = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        input_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        input_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(input_card, text="Playlist URL", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        playlist_input = ctk.CTkFrame(input_card, fg_color="transparent")
        playlist_input.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        playlist_input.grid_columnconfigure(0, weight=1)
        self.playlist_url_entry = ctk.CTkEntry(
            playlist_input, placeholder_text="https://www.youtube.com/playlist?list=...",
            height=44, font=("Segoe UI", 13), corner_radius=12,
            fg_color=INPUT, border_color=BORDER, border_width=1)
        self.playlist_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.playlist_url_entry.bind("<Return>", lambda e: self.analyze_playlist())
        ctk.CTkButton(playlist_input, text="Paste", width=80, height=44, corner_radius=10,
                      command=lambda: self.paste_into(self.playlist_url_entry),
                      fg_color=SECONDARY, hover_color="#2b3b51").grid(row=0, column=1, padx=2)
        self.playlist_analyze_btn = ctk.CTkButton(
            playlist_input, text="Analyze", width=112, height=44, corner_radius=10,
            command=self.analyze_playlist, font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self.playlist_analyze_btn.grid(row=0, column=2, padx=(8, 0))

        options_card = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        options_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        options_card.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(options_card, text="Download Options", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(16, 12))

        mode_frame = ctk.CTkFrame(options_card, fg_color=INPUT, corner_radius=12)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 16))
        self.playlist_mode_var = ctk.StringVar(value=self.mode_var.get())
        ctk.CTkRadioButton(mode_frame, text="🎬 Video", variable=self.playlist_mode_var, value="video",
                           command=lambda: self.on_mode_change("playlist"), font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)
        ctk.CTkRadioButton(mode_frame, text="🎵 Audio", variable=self.playlist_mode_var, value="audio",
                           command=lambda: self.on_mode_change("playlist"), font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)
        ctk.CTkRadioButton(mode_frame, text="🛠️ Custom", variable=self.playlist_mode_var, value="custom",
                           command=lambda: self.on_mode_change("playlist"), font=("Segoe UI", 12)).pack(side="left", padx=20, pady=12)

        self.playlist_video_quality_combo = ctk.CTkComboBox(options_card, values=["best", "2160 (4K)", "1440 (2K)", "1080", "720", "480", "360"],
                                                           fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        ctk.CTkLabel(options_card, text="Quality", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 4))
        self.playlist_video_quality_combo.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.playlist_video_quality_combo.set(self.video_quality_combo.get())

        self.playlist_audio_format_combo = ctk.CTkComboBox(options_card, values=["mp3", "m4a", "opus", "flac", "wav", "best"],
                                                           fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        ctk.CTkLabel(options_card, text="Audio Format", font=("Segoe UI", 12)).grid(row=2, column=1, sticky="w", padx=20, pady=(0, 4))
        self.playlist_audio_format_combo.grid(row=3, column=1, sticky="ew", padx=20, pady=(0, 12))
        self.playlist_audio_format_combo.set(self.audio_format_combo.get())

        ctk.CTkLabel(options_card, text="Save to", font=("Segoe UI", 12)).grid(row=2, column=2, sticky="w", padx=20, pady=(0, 4))
        playlist_folder_row = ctk.CTkFrame(options_card, fg_color="transparent")
        playlist_folder_row.grid(row=3, column=2, sticky="ew", padx=20, pady=(0, 12))
        playlist_folder_row.grid_columnconfigure(0, weight=1)
        self.playlist_folder_entry = ctk.CTkEntry(playlist_folder_row, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
        self.playlist_folder_entry.grid(row=0, column=0, sticky="ew")
        self.playlist_folder_entry.insert(0, str(self.download_dir))
        ctk.CTkButton(playlist_folder_row, text="📁", width=36, command=lambda: self.browse_folder("playlist"), fg_color="#3a3a3a").grid(row=0, column=1, padx=(6, 0))

        playlist_toggles = ctk.CTkFrame(options_card, fg_color="transparent")
        playlist_toggles.grid(row=4, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 8))
        self.playlist_embed_thumb_var = ctk.BooleanVar(value=self.embed_thumb_var.get())
        self.playlist_embed_meta_var = ctk.BooleanVar(value=self.embed_meta_var.get())
        self.playlist_subs_var = ctk.BooleanVar(value=self.subs_var.get())
        self.playlist_var = ctk.BooleanVar(value=False)
        self.playlist_aria2c_var = ctk.BooleanVar(value=self.aria2c_var.get())
        self.playlist_sponsorblock_var = ctk.BooleanVar(value=self.sponsorblock_var.get())
        for text, variable in (("Embed Thumbnail", self.playlist_embed_thumb_var), ("Embed Metadata", self.playlist_embed_meta_var),
                               ("Embed Subtitles", self.playlist_subs_var), ("Playlist", self.playlist_var)):
            ctk.CTkCheckBox(playlist_toggles, text=text, variable=variable, font=("Segoe UI", 11)).pack(side="left", padx=8, pady=4)
        playlist_toggles2 = ctk.CTkFrame(options_card, fg_color="transparent")
        playlist_toggles2.grid(row=5, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 8))
        ctk.CTkCheckBox(playlist_toggles2, text="Use aria2c (faster)", variable=self.playlist_aria2c_var, font=("Segoe UI", 11)).pack(side="left", padx=8, pady=4)
        ctk.CTkCheckBox(playlist_toggles2, text="SponsorBlock", variable=self.playlist_sponsorblock_var, font=("Segoe UI", 11)).pack(side="left", padx=8, pady=4)

        self.playlist_custom_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.playlist_custom_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 16))
        self.playlist_custom_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.playlist_custom_frame, text="Custom Command Template", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.playlist_custom_combo = ctk.CTkComboBox(self.playlist_custom_frame, values=[t["name"] for t in self.template_mgr.get_templates()],
                                                     fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8,
                                                     command=lambda name: self.on_template_select(name, "playlist"))
        self.playlist_custom_combo.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.playlist_custom_entry = ctk.CTkEntry(self.playlist_custom_frame, placeholder_text='e.g., -f "bv*[height<=1080]+ba/b" --embed-metadata {url}',
                                                  fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8, height=36)
        self.playlist_custom_entry.grid(row=2, column=0, sticky="ew")
        if self.template_mgr.get_templates():
            self.playlist_custom_entry.insert(0, self.template_mgr.get_templates()[0]["command"])
        self.on_mode_change("playlist")

        self.playlist_status_label = ctk.CTkLabel(page, text="Paste a playlist URL and analyze it.",
                                                   text_color=MUTED, anchor="w")
        self.playlist_status_label.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.playlist_scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        self.playlist_scroll.grid(row=4, column=0, sticky="nsew")

    def paste_into(self, entry):
        value = get_clipboard_text()
        if value:
            entry.delete(0, "end")
            entry.insert(0, value)

    def analyze_playlist(self):
        url = self.playlist_url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a playlist URL")
            return
        if not is_valid_url(url):
            messagebox.showwarning("Invalid URL", "URL must start with http:// or https://")
            return

        self.playlist_analyze_btn.configure(state="disabled", text="Analyzing...")
        self.playlist_status_label.configure(text="Analyzing playlist...")

        def do_analyze():
            try:
                downloader = VideoManDownloader(str(self.download_dir))
                info = downloader.get_video_info(url, use_cookies=bool(self.settings_mgr.get("cookies_browser")))
                self.root.after(0, lambda: self.show_playlist_entries(info))
            except Exception as e:
                self.root.after(0, lambda: self.playlist_status_label.configure(text=f"Analyze failed: {str(e)[:160]}"))
                self.root.after(0, lambda: messagebox.showerror("Analyze Failed", str(e)[:500]))
            finally:
                self.root.after(0, lambda: self.playlist_analyze_btn.configure(state="normal", text="Analyze"))

        threading.Thread(target=do_analyze, daemon=True).start()

    def show_playlist_entries(self, info):
        for widget in self.playlist_scroll.winfo_children():
            widget.destroy()
        self.playlist_entries = [entry for entry in (info.get("entries") or []) if entry]
        self.playlist_tasks.clear()
        self.playlist_scroll.grid_columnconfigure(0, weight=1)
        if not self.playlist_entries:
            self.playlist_status_label.configure(text="No downloadable entries found.")
            return
        self.playlist_status_label.configure(text=f"{len(self.playlist_entries)} entries found. Select videos and download them individually.")
        for index, entry in enumerate(self.playlist_entries):
            self.create_playlist_entry_tile(index, entry)

    def create_playlist_entry_tile(self, index, entry):
        tile = ctk.CTkFrame(self.playlist_scroll, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=12)
        tile.grid(row=index, column=0, sticky="ew", pady=5)
        tile.grid_columnconfigure(1, weight=1)
        selected = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tile, text="", variable=selected, width=28).grid(row=0, column=0, rowspan=2, padx=(14, 8), pady=14)
        title = entry.get("title") or f"Entry {index + 1}"
        ctk.CTkLabel(tile, text=f"{index + 1}. {title[:90]}", font=("Segoe UI", 12, "bold"), anchor="w").grid(
            row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 2))
        detail = entry.get("uploader") or entry.get("channel") or ""
        ctk.CTkLabel(tile, text=detail, text_color=MUTED, anchor="w").grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 12))
        status = ctk.CTkLabel(tile, text="Ready", text_color=MUTED, width=125)
        status.grid(row=0, column=2, rowspan=2, padx=6)
        download_btn = ctk.CTkButton(tile, text="Download", width=105, command=lambda: self.download_playlist_entry(
            index, entry, selected, status, download_btn, cancel_btn))
        download_btn.grid(row=0, column=3, rowspan=2, padx=5)
        cancel_btn = ctk.CTkButton(tile, text="Cancel", width=85, state="disabled", fg_color=SECONDARY,
                                   hover_color="#2b3b51", command=lambda: self.cancel_playlist_entry(index, status, cancel_btn))
        cancel_btn.grid(row=0, column=4, rowspan=2, padx=(0, 14))

    def download_playlist_entry(self, index, entry, selected, status, download_btn, cancel_btn):
        if not selected.get() or index in self.playlist_tasks:
            return
        url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url")
        if not url:
            status.configure(text="No URL")
            return
        folder = Path(self.playlist_folder_entry.get())
        folder.mkdir(parents=True, exist_ok=True)
        config = self.get_current_config("playlist")
        config["download_playlist"] = False
        downloader = VideoManDownloader(str(folder), log_callback=self.log)
        self.playlist_tasks[index] = downloader
        download_btn.configure(state="disabled", text="Downloading...")
        cancel_btn.configure(state="normal")
        status.configure(text="Starting...")

        def progress(data):
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes", 0)
                if total:
                    self.root.after(0, lambda: status.configure(text=f"{downloaded / total * 100:.0f}%"))

        downloader.progress_callback = progress

        def run():
            try:
                success = downloader.download(url, config)
                self.root.after(0, lambda: self.finish_playlist_entry(index, success, status, download_btn, cancel_btn))
            except Exception as error:
                self.root.after(0, lambda: self.finish_playlist_entry(index, False, status, download_btn, cancel_btn, str(error)))
        threading.Thread(target=run, daemon=True).start()

    def finish_playlist_entry(self, index, success, status, download_btn, cancel_btn, error=""):
        self.playlist_tasks.pop(index, None)
        status.configure(text="Complete" if success else ("Cancelled" if not error else "Failed"))
        if error:
            self.log(f"Playlist entry failed: {error}")
        download_btn.configure(state="normal", text="Download")
        cancel_btn.configure(state="disabled", text="Cancel")

    def cancel_playlist_entry(self, index, status, cancel_btn):
        downloader = self.playlist_tasks.get(index)
        if downloader:
            downloader.cancel()
            cancel_btn.configure(state="disabled", text="Cancelling...")
            status.configure(text="Cancelling...")

    def create_downloads_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["downloads"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(page, text="Downloads", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w", pady=(0,16))

        # Log view
        self.log_text = ctk.CTkTextbox(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=12, font=("Consolas", 11))
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_text.insert("0.0", "Download logs will appear here...\n")
        
        clear_btn = ctk.CTkButton(page, text="Clear Log", width=100, command=lambda: self.log_text.delete("0.0", "end"),
                     fg_color=SECONDARY, hover_color="#2b3b51")
        clear_btn.grid(row=2, column=0, sticky="e", pady=12)

        open_folder_btn = ctk.CTkButton(page, text="Open Download Folder", command=self.open_download_folder,
                           fg_color=SECONDARY, hover_color="#2b3b51")
        open_folder_btn.grid(row=2, column=0, sticky="w", pady=12)

    def create_settings_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["settings"] = page
        page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(page, text="Settings", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w", pady=(0,16))

        scroll = ctk.CTkScrollableFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Download dir
        ctk.CTkLabel(scroll, text="Default Download Directory", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(16,4))
        dir_row = ctk.CTkFrame(scroll, fg_color="transparent")
        dir_row.grid(row=1, column=0, sticky="ew", padx=16)
        dir_row.grid_columnconfigure(0, weight=1)
        self.settings_dir_entry = ctk.CTkEntry(dir_row, fg_color=INPUT, border_color=BORDER, border_width=1)
        self.settings_dir_entry.grid(row=0, column=0, sticky="ew")
        self.settings_dir_entry.insert(0, self.settings_mgr.get("download_dir"))
        ctk.CTkButton(dir_row, text="Browse", width=80, command=self.browse_settings_folder).grid(row=0, column=1, padx=(8,0))

        # Output template
        ctk.CTkLabel(scroll, text="Output Template (yt-dlp format)", font=("Segoe UI", 12, "bold")).grid(row=2, column=0, sticky="w", padx=16, pady=(16,4))
        self.template_entry = ctk.CTkEntry(scroll, fg_color=INPUT, border_color=BORDER, border_width=1)
        self.template_entry.grid(row=3, column=0, sticky="ew", padx=16)
        self.template_entry.insert(0, self.settings_mgr.get("output_template"))
        ctk.CTkLabel(scroll, text="Variables: %(title)s, %(id)s, %(ext)s, %(uploader)s, %(playlist)s etc", 
                    font=("Segoe UI", 10), text_color="#666").grid(row=4, column=0, sticky="w", padx=16, pady=(2,0))

        # Video height
        ctk.CTkLabel(scroll, text="Preferred Video Height", font=("Segoe UI", 12, "bold")).grid(row=5, column=0, sticky="w", padx=16, pady=(16,4))
        self.settings_quality_combo = ctk.CTkComboBox(scroll, values=["best", "2160", "1440", "1080", "720", "480", "360"],
                                                      fg_color=INPUT, border_color=BORDER, border_width=1)
        self.settings_quality_combo.grid(row=6, column=0, sticky="ew", padx=16)
        self.settings_quality_combo.set(self.settings_mgr.get("video_height"))

        # Audio format
        ctk.CTkLabel(scroll, text="Preferred Audio Format", font=("Segoe UI", 12, "bold")).grid(row=7, column=0, sticky="w", padx=16, pady=(16,4))
        self.settings_audio_combo = ctk.CTkComboBox(scroll, values=["mp3", "m4a", "opus", "flac", "wav"],
                                                   fg_color=INPUT, border_color=BORDER, border_width=1)
        self.settings_audio_combo.grid(row=8, column=0, sticky="ew", padx=16)
        self.settings_audio_combo.set(self.settings_mgr.get("audio_format"))

        # Cookies
        ctk.CTkLabel(scroll, text="Cookies from Browser (for age-restricted / private)", font=("Segoe UI", 12, "bold")).grid(row=9, column=0, sticky="w", padx=16, pady=(16,4))
        self.cookies_combo = ctk.CTkComboBox(scroll, values=["", "chrome", "firefox", "edge", "brave", "opera"],
                                            fg_color=INPUT, border_color=BORDER, border_width=1)
        self.cookies_combo.grid(row=10, column=0, sticky="ew", padx=16)
        self.cookies_combo.set(self.settings_mgr.get("cookies_browser"))

        # Save button
        ctk.CTkButton(scroll, text="Save Settings", command=self.save_settings).grid(row=11, column=0, sticky="ew", padx=16, pady=24)

    def create_templates_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["templates"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0,16))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Custom Command Templates", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Save reusable yt-dlp commands with the {url} placeholder", 
                    font=("Segoe UI", 11), text_color="#888").grid(row=1, column=0, sticky="w")
        
        self.templates_scroll = ctk.CTkScrollableFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        self.templates_scroll.grid(row=1, column=0, sticky="nsew")
        self.templates_scroll.grid_columnconfigure(0, weight=1)

        self.refresh_templates_ui()

        add_frame = ctk.CTkFrame(page, fg_color="transparent")
        add_frame.grid(row=2, column=0, sticky="ew", pady=16)
        add_frame.grid_columnconfigure(0, weight=1)
        add_frame.grid_columnconfigure(1, weight=2)

        self.new_template_name = ctk.CTkEntry(add_frame, placeholder_text="Template name", fg_color=INPUT, border_color=BORDER, border_width=1)
        self.new_template_name.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.new_template_cmd = ctk.CTkEntry(add_frame, placeholder_text='Command, e.g., -f "bv*[height<=1080]+ba/b" {url}',
                                           fg_color=INPUT, border_color=BORDER, border_width=1)
        self.new_template_cmd.grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkButton(add_frame, text="Add", width=80, command=self.add_template).grid(row=0, column=2, padx=(8,0))

    def create_about_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pages["about"] = page
        page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(page, text="▶", font=("Segoe UI", 64, "bold"), text_color=ACCENT).grid(row=0, column=0, pady=(40,16))
        ctk.CTkLabel(page, text="Video Man", font=("Segoe UI", 24, "bold")).grid(row=1, column=0)
        ctk.CTkLabel(page, text="Video/Audio Downloader based on yt-dlp", font=("Segoe UI", 13), text_color="#888").grid(row=2, column=0, pady=(4,20))

        info = ctk.CTkFrame(page, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14)
        info.grid(row=3, column=0, sticky="ew", padx=40, pady=20)
        info.grid_columnconfigure(0, weight=1)

        texts = [
            ("Application", "Video and audio downloader"),
            ("yt-dlp", "The download engine"),
            ("Platform", "Windows desktop"),
            ("Version", "1.0.0 (Windows)"),
            ("License", "GPLv3 - Free and Open Source"),
        ]
        for i, (k,v) in enumerate(texts):
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=20, pady=8)
            ctk.CTkLabel(row, text=k, font=("Segoe UI", 12, "bold"), width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=v, font=("Segoe UI", 12), anchor="w").pack(side="left")

        btns = ctk.CTkFrame(page, fg_color="transparent")
        btns.grid(row=4, column=0, pady=20)
        ctk.CTkButton(btns, text="yt-dlp", fg_color=SECONDARY, hover_color="#2b3b51",
                     command=lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp")).pack(side="left", padx=8)

    # ===== LOGIC =====
    def check_dependencies(self):
        ffmpeg_ok = check_ffmpeg(self.settings_mgr.get("ffmpeg_path"))
        aria2c_ok = check_aria2c(self.settings_mgr.get("aria2c_path"))
        status = []
        status.append(f"ffmpeg: {'✅' if ffmpeg_ok else '❌ Missing (needed for merging)'}")
        status.append(f"aria2c: {'✅' if aria2c_ok else '⚪ Optional'}")
        self.ffmpeg_status_label.configure(text=" | ".join(status))
        if not ffmpeg_ok:
            self.log("⚠️ ffmpeg not found. Install via 'winget install Gyan.FFmpeg' or add to PATH. Some features may fail.")

    def auto_paste_clipboard(self):
        text = get_clipboard_text()
        if is_valid_url(text):
            self.url_entry.insert(0, text)
            self.log(f"Auto-pasted URL from clipboard: {text}")

    def paste_url(self):
        text = get_clipboard_text()
        if text:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, text)

    def browse_folder(self, tab="home"):
        folder = filedialog.askdirectory(initialdir=str(self.download_dir))
        if folder:
            entry = self.folder_entry if tab == "home" else self.playlist_folder_entry
            entry.delete(0, "end")
            entry.insert(0, folder)
            self.download_dir = Path(folder)

    def browse_settings_folder(self):
        folder = filedialog.askdirectory(initialdir=self.settings_mgr.get("download_dir"))
        if folder:
            self.settings_dir_entry.delete(0, "end")
            self.settings_dir_entry.insert(0, folder)

    def open_download_folder(self):
        path = Path(self.folder_entry.get() if hasattr(self, 'folder_entry') else self.settings_mgr.get("download_dir"))
        if path.exists():
            os.startfile(str(path))
        else:
            messagebox.showwarning("Not found", f"Folder does not exist: {path}")

    def log(self, msg: str):
        print(msg)
        if hasattr(self, 'log_text'):
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")

    def on_mode_change(self, tab="home"):
        prefix = "" if tab == "home" else "playlist_"
        mode = getattr(self, f"{prefix}mode_var").get()
        quality_combo = getattr(self, f"{prefix}video_quality_combo")
        audio_combo = getattr(self, f"{prefix}audio_format_combo")
        custom_frame = getattr(self, f"{prefix}custom_frame")
        if mode == "video":
            quality_combo.configure(state="normal")
            audio_combo.configure(state="disabled")
            custom_frame.grid_remove()
        elif mode == "audio":
            quality_combo.configure(state="disabled")
            audio_combo.configure(state="normal")
            custom_frame.grid_remove()
        else:  # custom
            quality_combo.configure(state="disabled")
            audio_combo.configure(state="disabled")
            custom_frame.grid()

    def on_template_select(self, name, tab="home"):
        entry = self.custom_entry if tab == "home" else self.playlist_custom_entry
        for t in self.template_mgr.get_templates():
            if t["name"] == name:
                entry.delete(0, "end")
                entry.insert(0, t["command"])
                break

    def analyze_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL")
            return
        if not is_valid_url(url):
            messagebox.showwarning("Invalid URL", "URL must start with http:// or https://")
            return

        self.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.status_label.configure(text=f"Analyzing {url[:60]}...")
        self.log(f"🔍 Analyzing: {url}")

        def do_analyze():
            try:
                downloader = VideoManDownloader(str(self.download_dir))
                info = downloader.get_video_info(url, use_cookies=bool(self.settings_mgr.get("cookies_browser")))
                self.current_info = info

                # Update UI in main thread
                self.root.after(0, lambda: self.show_info(info))
                self.root.after(0, lambda: self.log(f"✅ Found: {info.get('title', 'Unknown')} | {info.get('uploader', '')}"))
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: self.log(f"❌ Analyze failed: {err}"))
                self.root.after(0, lambda: messagebox.showerror("Analyze Failed", err[:500]))
            finally:
                self.root.after(0, lambda: self.analyze_btn.configure(state="normal", text="Analyze"))

        threading.Thread(target=do_analyze, daemon=True).start()

    def show_info(self, info: Dict):
        title = info.get('title', 'Unknown Title')
        uploader = info.get('uploader', info.get('channel', ''))
        duration = info.get('duration', 0)
        
        self.title_label.configure(text=title[:80])
        self.uploader_label.configure(text=uploader)
        if duration:
            mins, secs = divmod(int(duration), 60)
            hours, mins = divmod(mins, 60)
            if hours:
                dur_str = f"{hours}:{mins:02d}:{secs:02d}"
            else:
                dur_str = f"{mins}:{secs:02d}"
            self.duration_label.configure(text=f"Duration: {dur_str} | Extractor: {info.get('extractor_key', '')}")
        else:
            self.duration_label.configure(text=f"Extractor: {info.get('extractor_key', '')} | Entries: {len(info.get('entries', [])) if 'entries' in info else 1}")

        self.info_card.grid(row=1, column=0, sticky="ew", pady=(0,16))
        # TODO: load thumbnail async

    def get_current_config(self, tab="home") -> Dict[str, Any]:
        prefix = "" if tab == "home" else "playlist_"
        get_control = lambda name: getattr(self, f"{prefix}{name}")
        # Parse quality
        quality_val = get_control("video_quality_combo").get().split()[0]
        audio_fmt = get_control("audio_format_combo").get()

        config = {
            "mode": get_control("mode_var").get(),
            "video_height": quality_val,
            "audio_format": audio_fmt,
            "audio_quality": "0",
            "output_template": self.settings_mgr.get("output_template"),
            "download_playlist": get_control("playlist_var").get(),
            "embed_thumbnail": get_control("embed_thumb_var").get(),
            "embed_metadata": get_control("embed_meta_var").get(),
            "embed_subtitles": get_control("subs_var").get(),
            "auto_subs": False,
            "sub_langs": ["en"],
            "use_aria2c": get_control("aria2c_var").get(),
            "sponsorblock": get_control("sponsorblock_var").get(),
            "embed_chapters": True,
            "cookies_browser": self.settings_mgr.get("cookies_browser"),
            "custom_template": get_control("custom_entry").get() if get_control("mode_var").get() == "custom" else "",
        }
        return config

    def progress_hook(self, d):
        # Called from yt-dlp thread
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            if total:
                pct = downloaded / total
                self.root.after(0, lambda: self.progress_bar.set(pct))
                self.root.after(0, lambda: self.status_label.configure(
                    text=f"Downloading: {pct*100:.1f}% | {format_bytes(downloaded)}/{format_bytes(total)}"))
            if speed:
                self.root.after(0, lambda: self.speed_label.configure(text=f"{format_speed(speed)} | ETA {eta}s" if eta else f"{format_speed(speed)}"))
        elif status == 'finished':
            self.root.after(0, lambda: self.status_label.configure(text="Post-processing..."))
            self.root.after(0, lambda: self.progress_bar.set(0.9))

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL")
            return
        if self.is_downloading:
            return

        folder = Path(self.folder_entry.get())
        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Folder Error", f"Cannot create folder: {e}")
                return
        self.download_dir = folder
        self.settings_mgr.set("download_dir", str(folder))

        config = self.get_current_config()
        self.log(f"⬇️ Starting download: {url}")
        self.log(f"Config: {config}")

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="Downloading...")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0.1)

        def on_complete():
            self.root.after(0, self.on_download_complete)
        def on_error(err_msg):
            self.root.after(0, lambda: self.on_download_error(err_msg))

        self.downloader = VideoManDownloader(str(folder), progress_callback=self.progress_hook, log_callback=self.log)
        
        def run():
            try:
                success = self.downloader.download(url, config)
                if success:
                    on_complete()
                elif self.is_downloading:
                    self.root.after(0, self.on_download_cancelled)
            except Exception as e:
                on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def on_download_complete(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ Download")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="✅ Download complete!")
        self.speed_label.configure(text="")
        self.log("✅ Download complete!")
        messagebox.showinfo("Complete", f"Download finished!\nSaved to: {self.download_dir}")

    def on_download_error(self, err_msg):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ Download")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text=f"❌ Error: {err_msg[:80]}")
        self.log(f"❌ Error: {err_msg}")
        messagebox.showerror("Download Failed", err_msg[:800])

    def cancel_download(self):
        if self.downloader:
            self.downloader.cancel()
        self.cancel_btn.configure(state="disabled", text="Cancelling...")
        self.status_label.configure(text="Cancelling...")
        self.log("Cancelled by user")

    def on_download_cancelled(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ Download")
        self.cancel_btn.configure(state="disabled", text="Cancel")
        self.progress_bar.set(0)
        self.speed_label.configure(text="")
        self.status_label.configure(text="Cancelled")

    def save_settings(self):
        self.settings_mgr.set("download_dir", self.settings_dir_entry.get())
        self.settings_mgr.set("output_template", self.template_entry.get())
        self.settings_mgr.set("video_height", self.settings_quality_combo.get().split()[0])
        self.settings_mgr.set("audio_format", self.settings_audio_combo.get())
        self.settings_mgr.set("cookies_browser", self.cookies_combo.get())
        messagebox.showinfo("Saved", "Settings saved!")
        self.log("Settings saved")

    def refresh_templates_ui(self):
        # Clear
        for w in self.templates_scroll.winfo_children():
            w.destroy()
        for idx, t in enumerate(self.template_mgr.get_templates()):
            row = ctk.CTkFrame(self.templates_scroll, fg_color=INPUT, border_color=BORDER, border_width=1, corner_radius=8)
            row.grid(row=idx, column=0, sticky="ew", pady=4, padx=4)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=t["name"], font=("Segoe UI", 11, "bold"), width=160, anchor="w").grid(row=0, column=0, padx=12, pady=8, sticky="w")
            ctk.CTkLabel(row, text=t["command"][:70], font=("Consolas", 10), text_color="#888", anchor="w").grid(row=0, column=1, padx=8, pady=8, sticky="w")
            ctk.CTkButton(row, text="Use", width=50, command=lambda cmd=t["command"]: self.use_template(cmd)).grid(row=0, column=2, padx=4)
            ctk.CTkButton(row, text="✕", width=30, fg_color="#4a2a2a", hover_color="#6a3a3a",
                         command=lambda i=idx: self.delete_template(i)).grid(row=0, column=3, padx=4)

    def use_template(self, cmd):
        self.mode_var.set("custom")
        self.on_mode_change()
        self.custom_entry.delete(0, "end")
        self.custom_entry.insert(0, cmd)
        self.switch_page("home")

    def delete_template(self, idx):
        self.template_mgr.remove_template(idx)
        self.refresh_templates_ui()
        # Update combo
        self.custom_combo.configure(values=[t["name"] for t in self.template_mgr.get_templates()])

    def add_template(self):
        name = self.new_template_name.get().strip()
        cmd = self.new_template_cmd.get().strip()
        if not name or not cmd:
            messagebox.showwarning("Missing", "Enter both name and command")
            return
        self.template_mgr.add_template(name, cmd)
        self.new_template_name.delete(0, "end")
        self.new_template_cmd.delete(0, "end")
        self.refresh_templates_ui()
        self.custom_combo.configure(values=[t["name"] for t in self.template_mgr.get_templates()])

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VideoManApp()
    app.run()
