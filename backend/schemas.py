# Last Edited: 2026-03-12
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class KolPostIn(BaseModel):
    kol_handle: str
    kol_name: Optional[str] = None
    kol_avatar_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    text: Optional[str] = None
    image_urls: List[str] = []
    likes: Optional[int] = 0
    retweets: Optional[int] = 0
    replies: Optional[int] = 0
    url: str


class KolPostList(BaseModel):
    items: List[KolPostIn]


class BrowseLogIn(BaseModel):
    visited_at: Optional[datetime] = None
    url: str
    kol_handle: Optional[str] = None
    kol_post_url: Optional[str] = None
    session_id: Optional[str] = None


class BrowseLogList(BaseModel):
    items: List[BrowseLogIn]


class UrlComparePayload(BaseModel):
    urls: List[str] = Field(default_factory=list)


class TrashBatchPayload(BaseModel):
    ids: List[int] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)


class PushTgPayload(BaseModel):
    url: str


class TweetCollectItem(BaseModel):
    id: str
    name: Optional[str] = "Unknown"
    user_handle: Optional[str] = "Unknown"
    tags: Optional[str] = ""
    primary_tag: Optional[str] = "自动定时"
    full_text: str
    translated_text: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    captured_at: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class CollectPayload(BaseModel):
    auth: str
    data: List[TweetCollectItem] = Field(default_factory=list)


class TopicBuildPayload(BaseModel):
    topic_name: str
    topic_type: str = "event"
    description: Optional[str] = None
    item_ids: List[int] = Field(default_factory=list)


class TopicAnalyzePayload(BaseModel):
    focus: Optional[str] = None


class YoutubeImportPayload(BaseModel):
    urls: List[str] = Field(default_factory=list)
    channel_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class YoutubeAnalyzePayload(BaseModel):
    item_ids: List[int] = Field(default_factory=list)


class CryptoPullPayload(BaseModel):
    metric_name: str
    symbol: str
    market_type: str = "spot"
    interval: str = "1h"
    value: float
    timestamp: Optional[datetime] = None


class CryptoBackfillPayload(BaseModel):
    metric_name: str
    symbol: str
    market_type: str = "spot"
    interval: str = "1h"
    start_time: datetime
    end_time: datetime
    values: List[float] = Field(default_factory=list)


class ChartCapturePayload(BaseModel):
    page_url: str
    platform: str
    symbol: Optional[str] = None
    timeframe: str = "1h"
    image_path: str


class ChartAnalyzePayload(BaseModel):
    item_id: int


class ChartBatchCapturePayload(BaseModel):
    urls: List[str] = Field(default_factory=list)
    timeframe: str = "4h"
    platform: str = "coinglass"
    symbol: Optional[str] = None


class ChartPushTgPayload(BaseModel):
    item_ids: List[int] = Field(default_factory=list)
    message: str = ""


class BackupPayload(BaseModel):
    target_dir: str = "data/backup"
