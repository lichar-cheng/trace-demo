# Last Edited: 2026-03-12
import time
from typing import List

import requests

from .config import YoutubePipelineConfig


class YoutubeFetcher:
    def __init__(self, config: YoutubePipelineConfig):
        self.config = config

    def get_videos_after_date(self, channel_id: str, after_date: str) -> List[str]:
        if not self.config.api_key:
            return []
        video_urls: List[str] = []
        next_page_token = None

        while True:
            params = {
                "part": "snippet",
                "channelId": channel_id,
                "publishedAfter": after_date,
                "maxResults": 50,
                "type": "video",
                "order": "date",
                "key": self.config.api_key,
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            r = requests.get(self.config.base_url, params=params, proxies=self.config.proxies or None, timeout=20)
            if r.status_code != 200:
                break

            data = r.json()
            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            time.sleep(0.3)

        return video_urls
