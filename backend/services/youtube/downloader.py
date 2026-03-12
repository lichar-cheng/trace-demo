# Last Edited: 2026-03-12
import os
from pathlib import Path
from typing import Optional

from .config import YoutubePipelineConfig


class YoutubeDownloader:
    def __init__(self, config: YoutubePipelineConfig):
        self.config = config

    def download_audio(self, video_url: str) -> Optional[str]:
        try:
            import yt_dlp
        except Exception:
            return None

        output_dir = Path(self.config.audio_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ytdl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{output_dir}/%(channel)s_%(upload_date)s_%(title)s_%(id)s.%(ext)s",
            "sleep_interval_requests": 1.5,
            "ignoreerrors": True,
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if not info:
                    return None
                filename = ydl.prepare_filename(info)
                audio_path = os.path.splitext(filename)[0] + ".m4a"
                return audio_path if os.path.exists(audio_path) else None
        except Exception:
            return None
