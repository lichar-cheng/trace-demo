# Last Edited: 2026-03-12
import random
import time
from typing import Dict, List, Optional

from .config import YoutubePipelineConfig, default_channel_ids
from .downloader import YoutubeDownloader
from .fetcher import YoutubeFetcher
from .transcriber import YoutubeTranscriber


class YoutubePipeline:
    """拆分式 YouTube 流水线：拉取列表 -> 下载音频 -> 转写。"""

    def __init__(self, config: Optional[YoutubePipelineConfig] = None):
        self.config = (config or YoutubePipelineConfig()).normalize()
        self.fetcher = YoutubeFetcher(self.config)
        self.downloader = YoutubeDownloader(self.config)
        self.transcriber = YoutubeTranscriber(self.config)

    def collect_video_urls(self, channel_ids: Optional[List[str]], start_date: str) -> List[str]:
        channels = channel_ids or default_channel_ids()
        urls: List[str] = []
        for cid in channels:
            urls.extend(self.fetcher.get_videos_after_date(cid, start_date))
        return urls

    def process_urls(self, urls: List[str], sleep_min: float = 0.5, sleep_max: float = 1.5) -> List[Dict]:
        results = []
        for url in urls:
            row = {"url": url, "downloaded": False, "transcribed": False}
            audio = self.downloader.download_audio(url)
            if audio:
                row["downloaded"] = True
                row["audio_path"] = audio
                tr = self.transcriber.transcribe_audio(audio)
                row["transcribe"] = tr
                row["transcribed"] = bool(tr.get("ok"))
            results.append(row)
            time.sleep(random.uniform(sleep_min, sleep_max))
        return results
