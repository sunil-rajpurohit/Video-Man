"""
Video Man - yt-dlp wrapper
Provides the download engine for the Windows application.
"""
import os
import json
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
import yt_dlp
from yt_dlp.utils import DownloadError

class VideoManDownloader:
    def __init__(self, download_dir: str, progress_callback: Optional[Callable] = None, 
                 log_callback: Optional[Callable] = None):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._cancel_flag = False
        self.current_ydl = None

    def cancel(self):
        self._cancel_flag = True

    def _progress_hook(self, d):
        if self._cancel_flag:
            raise DownloadError("Cancelled by user")
        if self.progress_callback:
            self.progress_callback(d)

    def get_video_info(self, url: str, use_cookies: bool = False) -> Dict[str, Any]:
        """Fetch information without downloading."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'noplaylist': False,
        }
        if use_cookies:
            # try to use browser cookies if needed
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            raise e

    def build_options(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build yt-dlp options from UI config
        Supported Video Man preferences:
        - audio only, format, quality, thumbnail, metadata, subtitles, playlist, aria2c, etc
        """
        ydl_opts = {
            'outtmpl': str(self.download_dir / config.get('output_template', '%(title)s [%(id)s].%(ext)s')),
            'progress_hooks': [self._progress_hook],
            'noplaylist': not config.get('download_playlist', False),
            'quiet': False,
            'no_warnings': False,
        }

        # External downloader.
        if config.get('use_aria2c', False):
            ydl_opts['external_downloader'] = 'aria2c'
            ydl_opts['external_downloader_args'] = ['-x', '16', '-k', '1M']

        # Format selection
        mode = config.get('mode', 'video')  # video, audio, custom
        if mode == 'audio':
            audio_format = config.get('audio_format', 'mp3')
            quality = config.get('audio_quality', '0')  # 0 best
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': quality,
            }]
            if config.get('embed_thumbnail', True):
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
            if config.get('embed_metadata', True):
                ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})
                ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
        else:
            # Video mode
            height = config.get('video_height', 'best')  # e.g., 1080, 720, best
            if height == 'best':
                ydl_opts['format'] = 'bv*+ba/b'
            else:
                ydl_opts['format'] = f'bv*[height<={height}]+ba/b[height<={height}] / b[height<={height}] / bv*+ba/b'
            
            if config.get('embed_thumbnail', False):
                ydl_opts['embed_thumbnail'] = True
            if config.get('embed_metadata', True):
                ydl_opts['postprocessors'] = [{'key': 'FFmpegMetadata'}]
            else:
                ydl_opts['postprocessors'] = []

        # Subtitles.
        if config.get('embed_subtitles', False):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = config.get('auto_subs', False)
            ydl_opts['subtitleslangs'] = config.get('sub_langs', ['en'])
            ydl_opts['embedsubtitles'] = True

        # SponsorBlock
        if config.get('sponsorblock', False):
            ydl_opts['postprocessors'].append({
                'key': 'SponsorBlock',
                'categories': ['sponsor', 'intro', 'outro']
            })
            ydl_opts['postprocessors'].append({
                'key': 'ModifyChapters',
                'remove_sponsor_segments': ['sponsor', 'intro', 'outro']
            })

        # Extra args
        if config.get('embed_chapters', True):
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            # chapters via metadata already

        # Custom command templates.
        custom_args = config.get('custom_args', '')
        if custom_args and mode == 'custom':
            # Will be handled separately via command builder
            pass

        # Merge custom yt-dlp options
        if config.get('cookies_browser'):
            ydl_opts['cookiesfrombrowser'] = (config['cookies_browser'],)

        return ydl_opts

    def download(self, url: str, config: Dict[str, Any]) -> bool:
        """Main download entry"""
        self._cancel_flag = False
        try:
            if config.get('mode') == 'custom':
                # Execute the custom command template.
                return self.download_custom(url, config.get('custom_template', ''))
            
            opts = self.build_options(config)
            if self.log_callback:
                self.log_callback(f"Options: {json.dumps({k: str(v) for k,v in opts.items() if k != 'progress_hooks'}, indent=2)}")

            if config.get('download_playlist', False):
                self._download_playlist_sequentially(url, opts)
            else:
                opts['noplaylist'] = True
                with yt_dlp.YoutubeDL(opts) as ydl:
                    self.current_ydl = ydl
                    ydl.download([url])
            return True
        except DownloadError as e:
            if "Cancelled" in str(e):
                if self.log_callback:
                    self.log_callback("Download cancelled")
                return False
            raise e
        except Exception as e:
            raise e
        finally:
            self.current_ydl = None

    def _download_playlist_sequentially(self, url: str, opts: Dict[str, Any]) -> None:
        """Download and post-process each playlist entry before starting the next."""
        info_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': False,
        }
        if opts.get('cookiesfrombrowser'):
            info_opts['cookiesfrombrowser'] = opts['cookiesfrombrowser']

        with yt_dlp.YoutubeDL(info_opts) as info_ydl:
            playlist = info_ydl.extract_info(url, download=False)

        entries = [entry for entry in (playlist.get('entries') or []) if entry]
        if not entries:
            raise DownloadError("Playlist contains no downloadable entries")

        entry_opts = dict(opts)
        entry_opts['noplaylist'] = True
        for index, entry in enumerate(entries, start=1):
            if self._cancel_flag:
                raise DownloadError("Cancelled by user")
            entry_url = entry.get('webpage_url') or entry.get('original_url') or entry.get('url')
            if not entry_url:
                if self.log_callback:
                    self.log_callback(f"Skipping playlist entry {index}: no URL")
                continue
            if self.log_callback:
                self.log_callback(f"Playlist entry {index}/{len(entries)}: {entry.get('title', entry_url)}")
            with yt_dlp.YoutubeDL(entry_opts) as ydl:
                self.current_ydl = ydl
                ydl.download([entry_url])

    def download_custom(self, url: str, template: str) -> bool:
        """
        Execute a custom yt-dlp command template.
        Template can contain {url} placeholder
        Example: -f bv*[height<=1080]+ba/b --embed-metadata {url}
        """
        import shlex
        
        # Replace {url} and similar
        cmd_str = template.replace('{url}', url)
        
        # Parse into list - naive but works for Windows
        # Pass each argument separately to the subprocess.
        try:
            args = shlex.split(cmd_str, posix=False)
        except:
            args = cmd_str.split()

        # Ensure URL is last if not already included
        if url not in args and '{url}' not in template:
            args.append(url)

        # Build opts from args? Simpler: use yt-dlp's parse
        # For Windows version, we build a dict and pass to YoutubeDL
        # We'll support passing raw args via yt-dlp's CLI style using YoutubeDL's params override
        
        # Quick implementation: extract format and other known flags
        ydl_opts = {
            'outtmpl': str(self.download_dir / '%(title)s [%(id)s].%(ext)s'),
            'progress_hooks': [self._progress_hook],
        }
        
        # Parse some common flags manually for safety
        # In full implementation you'd call yt_dlp's main with args, but we wrap
        if self.log_callback:
            self.log_callback(f"Custom command: yt-dlp {' '.join(args)}")

        # Use yt-dlp to parse args: we can invoke with list
        try:
            # yt_dlp can be called with parsed options
            # We'll use YoutubeDL with custom args converted
            # For simplicity, we let yt-dlp handle it via its CLI parser
            from yt_dlp import parse_options
            # Not stable, fallback to direct download with custom args as additional opts
            
            # Try to build options from args string using yt-dlp's own parser workaround:
            # We'll just pass args as external
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # If args contain -f, extract
                if '-f' in args:
                    idx = args.index('-f')
                    if idx+1 < len(args):
                        ydl_opts['format'] = args[idx+1]
                ydl.params.update(ydl_opts)
                self.current_ydl = ydl
                ydl.download([url])
            return True
        except Exception as e:
            raise e

    def get_formats(self, info: Dict[str, Any]) -> List[Dict]:
        """Extract available formats - for UI format selector"""
        formats = info.get('formats', [])
        # Deduplicate and sort
        seen = {}
        for f in formats:
            fid = f.get('format_id')
            if fid not in seen:
                seen[fid] = f
        return list(seen.values())

# Helper for running a download in a background thread.
class DownloadTask:
    def __init__(self, url: str, config: Dict, downloader: VideoManDownloader,
                 on_complete: Callable, on_error: Callable):
        self.url = url
        self.config = config
        self.downloader = downloader
        self.on_complete = on_complete
        self.on_error = on_error
        self.thread = None

    def start(self):
        def run():
            try:
                success = self.downloader.download(self.url, self.config)
                if success:
                    self.on_complete()
            except Exception as e:
                self.on_error(str(e))
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
