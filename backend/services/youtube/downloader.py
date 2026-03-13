import re
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .config import YoutubePipelineConfig


class YoutubeDownloader:
    def __init__(self, config: YoutubePipelineConfig):
        self.config = config
        self.last_hit_cache = False

    def _extract_video_id(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            if parsed.netloc in {"youtu.be", "www.youtu.be"}:
                return parsed.path.strip("/")
            if "youtube.com" in parsed.netloc:
                if parsed.path == "/watch":
                    return parse_qs(parsed.query).get("v", [""])[0]
                match = re.search(r"/(shorts|embed)/([^/?]+)", parsed.path)
                if match:
                    return match.group(2)
        except Exception:
            return ""
        return ""

    def _find_existing_audio(self, video_id: str) -> Optional[str]:
        if not video_id:
            return None

        audio_dir = Path(self.config.audio_output_dir)
        if not audio_dir.exists():
            return None

        patterns = [
            f"*{video_id}*.mp3",
            f"*{video_id}*.m4a",
            f"*{video_id}*.webm",
            f"*{video_id}*.wav",
            f"*{video_id}*.opus",
        ]
        for pattern in patterns:
            matches = sorted(audio_dir.rglob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
            if matches:
                return str(matches[0])
        return None

    def download_audio(self, url: str) -> Optional[str]:
        self.last_hit_cache = False
        video_id = self._extract_video_id(url)
        cached = self._find_existing_audio(video_id)
        if cached:
            self.last_hit_cache = True
            return cached

        try:
            import yt_dlp
        except Exception:
            return None

        output_dir = Path(self.config.audio_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        YTDL_OPTS = {
            "ffmpeg_location": self.config.ffmpeg_location,
            'format': 'bestaudio/best',
            'outtmpl': f'{OUTPUT_DIR}/%(channel)s_%(upload_date)s_%(id)s.%(ext)s',
            'sleep_interval_requests': 1.5,
            'ignoreerrors': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None
                downloaded_id = info.get("id") or video_id
                filename = ydl.prepare_filename(info)
        except Exception:
            return None

        file_path = Path(filename)
        if file_path.exists():
            self.last_hit_cache = False
            return str(file_path)

        fallback = self._find_existing_audio(downloaded_id)
        self.last_hit_cache = bool(fallback)
        return fallback
