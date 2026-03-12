# Last Edited: 2026-03-12
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class YoutubePipelineConfig:
    api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    base_url: str = "https://www.googleapis.com/youtube/v3/search"
    proxies: Dict[str, str] = field(default_factory=lambda: {
        "http": os.getenv("YOUTUBE_PROXY_HTTP", ""),
        "https": os.getenv("YOUTUBE_PROXY_HTTPS", ""),
    })
    audio_output_dir: str = os.getenv("YOUTUBE_AUDIO_DIR", "./data/youtube/audio_lake")
    transcribe_output_dir: str = os.getenv("YOUTUBE_TRANSCRIBE_DIR", "./data/youtube/transcribe_output")
    model_size: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    language: str = os.getenv("WHISPER_LANGUAGE", "zh")
    device: str = os.getenv("WHISPER_DEVICE", "auto")
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "auto")

    def normalize(self):
        Path(self.audio_output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.transcribe_output_dir).mkdir(parents=True, exist_ok=True)
        self.proxies = {k: v for k, v in self.proxies.items() if v}
        return self


def default_channel_ids() -> List[str]:
    raw = os.getenv("YOUTUBE_CHANNEL_IDS", "")
    if not raw.strip():
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]
