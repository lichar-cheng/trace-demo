import base64
import binascii
import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import httpx
import requests
from flask import Blueprint, Flask, Response, jsonify, request, send_from_directory, session
from flask_cors import CORS
from pydantic import ValidationError

from models import SessionLocal, KolPost, BrowseLog, KnowledgeItem, Topic, EntityProfile, init_db
from services.youtube import YoutubePipeline
from schemas import (
    KolPostList,
    BrowseLogList,
    UrlComparePayload,
    TrashBatchPayload,
    PushTgPayload,
    CollectPayload,
    TopicBuildPayload,
    TopicAnalyzePayload,
    YoutubeImportPayload,
    YoutubeAnalyzePayload,
    CryptoPullPayload,
    CryptoBackfillPayload,
    ChartCapturePayload,
    ChartAnalyzePayload,
    BackupPayload,
)

BASE_DIR = os.path.dirname(__file__)

init_db()

AUTH_TOKEN = os.getenv("COLLECT_AUTH_TOKEN", "1")
APP_USERNAME = os.getenv("APP_LOGIN_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_LOGIN_PASSWORD", "trace-demo")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "trace-demo-fixed-secret")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "")
NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2025-09-03")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DATA_ROOT_DIR = os.getenv("DATA_ROOT_DIR", str(Path(BASE_DIR).parent / "data" / "x"))
UPLOAD_DIR = os.path.join(DATA_ROOT_DIR, "uploads")
IMAGES_DIR = os.path.join(DATA_ROOT_DIR, "images")
TRASH_DIR = os.path.join(DATA_ROOT_DIR, "trash")
COLLECT_FILE_PATTERN = "x_collect_*.json"
for _d in [DATA_ROOT_DIR, UPLOAD_DIR, IMAGES_DIR, TRASH_DIR]:
    os.makedirs(_d, exist_ok=True)

ASSETS_MAP = {
    "bitcoin": ["btc", "bitcoin", "sats"],
    "ethereum": ["eth", "ethereum", "vitalik"],
    "altcoin": ["sol", "bnb", "doge", "meme", "pepe", "altcoin"],
}
THEMES_MAP = {
    "macro": ["macro", "fed", "cpi", "ppi", "rate", "inflation"],
    "technical": ["technical", "rsi", "macd", "ma", "ema", "support", "resistance"],
    "cycle": ["cycle", "bull", "bear", "halving"],
}


def log_youtube(event: str, **kwargs):
    detail = " ".join(f"{key}={repr(value)}" for key, value in kwargs.items())
    print(f"[youtube] {event} {detail}".strip(), flush=True)


def log_collect(event: str, **kwargs):
    detail = " ".join(f"{key}={repr(value)}" for key, value in kwargs.items())
    print(f"[collect] {event} {detail}".strip(), flush=True)


def log_notion(event: str, **kwargs):
    detail = " ".join(f"{key}={repr(value)}" for key, value in kwargs.items())
    print(f"[notion] {event} {detail}".strip(), flush=True)


def normalize_handle(value: str) -> str:
    return (value or "unknown").strip().lstrip("@")


def fetch_youtube_title(url: str) -> str:
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = (info or {}).get("title") or ""
            if title.strip():
                return title.strip()
    except Exception as exc:
        log_youtube("title_fetch_failed", url=url, error=str(exc))
    return f"YouTube: {url}"


def fetch_youtube_metadata(url: str) -> dict:
    fallback = {
        "title": f"YouTube: {url}",
        "uploader": None,
        "publish_time": None,
        "upload_date": None,
    }
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        upload_date = info.get("upload_date")
        publish_time = None
        if upload_date and len(upload_date) == 8:
            publish_time = datetime.strptime(upload_date, "%Y%m%d")
        return {
            "title": (info.get("title") or fallback["title"]).strip(),
            "uploader": (info.get("uploader") or info.get("channel") or "").strip() or None,
            "publish_time": publish_time,
            "upload_date": upload_date,
        }
    except Exception as exc:
        log_youtube("metadata_fetch_failed", url=url, error=str(exc))
        return fallback


def title_from_media_path(path: str) -> str:
    filename = os.path.basename(path or "")
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r"[_-]([A-Za-z0-9_-]{11})$", "", stem)
    stem = re.sub(r"[_-]+", " ", stem).strip()
    return stem or filename or ""


def display_youtube_title(item) -> str:
    extra = parse_extra(item.extra_json)
    for candidate in [extra.get("display_title"), extra.get("video_title"), item.title]:
        value = (candidate or "").strip()
        if not value:
            continue
        if re.fullmatch(r"manual[_ ]item[_ ]\d+", value, re.IGNORECASE):
            continue
        if re.fullmatch(r"YouTube Video [A-Za-z0-9_-]{6,}", value, re.IGNORECASE):
            continue
        if re.match(r"^YouTube:\s*https?://", value, re.IGNORECASE):
            continue
        return value

    return item.url or f"YouTube {item.id}"


def safe_relative_path(value: str) -> str:
    parts = []
    for part in Path(str(value or "")).parts:
        if part in ("", ".", ".."):
            continue
        cleaned = re.sub(r"[^A-Za-z0-9._\-/ ]", "_", part).strip()
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts)


def split_possible_list(value):
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def resolve_image_reference(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://") or value.startswith("/images/"):
        return value

    normalized = safe_relative_path(value)
    if not normalized:
        return ""

    direct_path = Path(IMAGES_DIR) / normalized
    if direct_path.exists():
        rel_path = direct_path.relative_to(IMAGES_DIR).as_posix()
        return f"/images/{rel_path}"

    basename = Path(normalized).name
    matches = list(Path(IMAGES_DIR).rglob(basename))
    if matches:
        rel_path = matches[0].relative_to(IMAGES_DIR).as_posix()
        return f"/images/{rel_path}"
    return value


def normalize_source_rows(rows, source_key: str, source_label: str, bucket: str):
    items = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_copy = dict(row)
        image_values = (
            row_copy.get("image_urls")
            or row_copy.get("media_urls")
            or row_copy.get("local_media_paths")
            or row_copy.get("media_paths")
            or []
        )
        row_copy["image_urls"] = [resolved for resolved in (resolve_image_reference(v) for v in split_possible_list(image_values)) if resolved]
        row_copy["sourceDirectory"] = source_key
        row_copy["sourceDirectoryLabel"] = source_label
        row_copy["sourceBucket"] = bucket
        items.append(row_copy)
    return items


def load_x_source_payload():
    items = []
    directories = []

    source_specs = []
    source_specs.extend(("x", path) for path in sorted(Path(DATA_ROOT_DIR).glob(COLLECT_FILE_PATTERN)))
    source_specs.extend(("uploads", path) for path in sorted(Path(UPLOAD_DIR).glob("*.json")))

    for bucket, file_path in source_specs:
        rows = read_json_file(str(file_path))
        if isinstance(rows, dict):
            rows = rows.get("items", [])
        if not isinstance(rows, list):
            continue
        source_label = file_path.stem
        source_key = f"{bucket}/{source_label}"
        normalized_rows = normalize_source_rows(rows, source_key, source_label, bucket)
        items.extend(normalized_rows)
        directories.append({
            "name": source_key,
            "label": source_label,
            "count": len(normalized_rows),
            "bucket": bucket,
        })

    return {"items": items, "directories": directories}


def parse_basic_auth():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return None, None
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None, None
    if ":" not in decoded:
        return None, None
    username, password = decoded.split(":", 1)
    return username, password


def has_valid_login() -> bool:
    if session.get("authenticated"):
        return True
    username, password = parse_basic_auth()
    return username == APP_USERNAME and password == APP_PASSWORD


def auth_failed_response():
    response = jsonify({"error": "auth_required"})
    response.status_code = 401
    response.headers["WWW-Authenticate"] = 'Basic realm="Trace Demo"'
    return response


def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def notion_request(method: str, path: str, payload=None):
    if not NOTION_API_TOKEN or not (NOTION_DATA_SOURCE_ID or NOTION_DATABASE_ID):
        raise RuntimeError("notion_not_configured")
    log_notion("request", method=method.upper(), path=path)
    response = requests.request(
        method.upper(),
        f"https://api.notion.com{path}",
        headers=notion_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        log_notion("response_failed", method=method.upper(), path=path, status_code=response.status_code, body=response.text[:300])
        raise RuntimeError(f"notion_http_{response.status_code}: {response.text[:300]}")
    log_notion("response_ok", method=method.upper(), path=path, status_code=response.status_code)
    if not response.text:
        return {}
    return response.json()


def find_notion_property_name(properties: dict, property_type: str, preferred_names=None):
    preferred_names = preferred_names or []
    for name in preferred_names:
        prop = properties.get(name) or {}
        if prop.get("type") == property_type:
            return name
    for name, prop in properties.items():
        if prop.get("type") == property_type:
            return name
    return None


def notion_schema_path():
    if NOTION_DATA_SOURCE_ID:
        return f"/v1/data_sources/{NOTION_DATA_SOURCE_ID}"
    return f"/v1/databases/{NOTION_DATABASE_ID}"


def notion_parent_payload():
    if NOTION_DATA_SOURCE_ID:
        return {"data_source_id": NOTION_DATA_SOURCE_ID}
    return {"database_id": NOTION_DATABASE_ID}


def resolve_notion_schema():
    if NOTION_DATA_SOURCE_ID:
        log_notion("schema_resolve", mode="data_source_id", data_source_id=NOTION_DATA_SOURCE_ID)
        data_source = notion_request("GET", f"/v1/data_sources/{NOTION_DATA_SOURCE_ID}")
        return data_source, {"data_source_id": NOTION_DATA_SOURCE_ID}

    if NOTION_DATABASE_ID:
        log_notion("schema_resolve", mode="database_id", database_id=NOTION_DATABASE_ID)
        database_obj = notion_request("GET", f"/v1/databases/{NOTION_DATABASE_ID}")
        data_sources = database_obj.get("data_sources") or []
        if not data_sources:
            raise RuntimeError("notion_database_has_no_data_sources")
        first_source = data_sources[0] or {}
        resolved_data_source_id = first_source.get("id")
        if not resolved_data_source_id:
            raise RuntimeError("notion_database_missing_data_source_id")
        log_notion("schema_resolved_from_database", database_id=NOTION_DATABASE_ID, data_source_id=resolved_data_source_id)
        data_source = notion_request("GET", f"/v1/data_sources/{resolved_data_source_id}")
        return data_source, {"data_source_id": resolved_data_source_id}

    raise RuntimeError("notion_not_configured")


def notion_title_value(text: str):
    return {"title": [{"type": "text", "text": {"content": (text or "Untitled")[:200]}}]}


def notion_rich_text_value(text: str):
    return {"rich_text": [{"type": "text", "text": {"content": (text or "")[:1900]}}]}


def notion_summary_text(text: str, limit: int = 280):
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def notion_date_value(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return {"date": {"start": value.isoformat()}}
    return {"date": {"start": str(value)}}


def notion_url_value(value: str):
    if not value:
        return None
    return {"url": value}


def notion_status_name(status_value: str, options: list):
    mapping = {
        "pending": ["未开始", "Not started", "Todo", "To do", "Backlog"],
        "processing": ["进行中", "In progress", "Doing"],
        "done": ["已完成", "完成", "Done"],
        "failed": ["失败", "阻塞", "Blocked"],
    }
    expected = mapping.get(status_value, []) + [status_value]
    option_names = {option.get("name") for option in options or []}
    for candidate in expected:
        if candidate in option_names:
            return candidate
    return next(iter(option_names), None)


def chunk_text(text: str, limit: int = 1800):
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    current = []
    current_len = 0
    for line in text.splitlines():
        line = line.rstrip()
        additional = len(line) + (1 if current else 0)
        if current and current_len + additional > limit:
            chunks.append("\n".join(current).strip())
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += additional
    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def build_notion_transcript_blocks(item):
    transcript = (item.content_raw or item.content_cleaned or "").strip()
    if not transcript:
        return []
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Transcript"}}]
            },
        }
    ]
    for chunk in chunk_text(transcript):
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                },
            }
        )
    return blocks


def replace_notion_page_body(page_id: str, item, extra_payload: dict):
    old_block_ids = extra_payload.get("notion_transcript_block_ids") or []
    for block_id in old_block_ids:
        try:
            notion_request("DELETE", f"/v1/blocks/{block_id}")
            log_notion("body_block_deleted", page_id=page_id, block_id=block_id)
        except Exception as exc:
            log_notion("body_block_delete_failed", page_id=page_id, block_id=block_id, error=str(exc))

    blocks = build_notion_transcript_blocks(item)
    if not blocks:
        extra_payload["notion_transcript_block_ids"] = []
        return extra_payload

    response = notion_request(
        "PATCH",
        f"/v1/blocks/{page_id}/children",
        {"children": blocks},
    )
    block_ids = [block.get("id") for block in response.get("results", []) if block.get("id")]
    extra_payload["notion_transcript_block_ids"] = block_ids
    log_notion("body_blocks_replaced", page_id=page_id, block_count=len(block_ids))
    return extra_payload


def replace_notion_x_page_body(page_id: str, post_data: dict, extra_payload: dict):
    old_block_ids = extra_payload.get("notion_body_block_ids") or []
    for block_id in old_block_ids:
        try:
            notion_request("DELETE", f"/v1/blocks/{block_id}")
            log_notion("body_block_deleted", page_id=page_id, block_id=block_id)
        except Exception as exc:
            log_notion("body_block_delete_failed", page_id=page_id, block_id=block_id, error=str(exc))

    blocks = []
    body = (post_data.get("text") or "").strip()
    if body:
        for chunk in chunk_text(body):
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    },
                }
            )

    for image_url in post_data.get("image_urls") or []:
        absolute_url = image_url if str(image_url).startswith("http") else f"http://localhost:8000{image_url}"
        blocks.append(
            {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": absolute_url},
                },
            }
        )

    if not blocks:
        extra_payload["notion_body_block_ids"] = []
        return extra_payload

    response = notion_request("PATCH", f"/v1/blocks/{page_id}/children", {"children": blocks})
    block_ids = [block.get("id") for block in response.get("results", []) if block.get("id")]
    extra_payload["notion_body_block_ids"] = block_ids
    log_notion("body_blocks_replaced", page_id=page_id, block_count=len(block_ids))
    return extra_payload


def build_notion_youtube_properties(item, data_source_properties: dict):
    extra = parse_extra(item.extra_json)
    transcript = (item.content_raw or item.content_cleaned or "").strip()
    note_lines = [
        f"Author: {item.author_name or extra.get('uploader') or ''}".strip(),
        f"Time: {item.publish_time.isoformat() if item.publish_time else extra.get('publish_time') or extra.get('upload_date') or ''}".strip(),
        notion_summary_text(transcript, 240).strip(),
    ]
    note_text = "\n".join(line for line in note_lines if line).strip()

    properties = {}
    title_name = find_notion_property_name(data_source_properties, "title", ["名称", "Name", "标题"])
    note_name = find_notion_property_name(data_source_properties, "rich_text", ["备注", "Note", "Notes"])
    date_name = find_notion_property_name(data_source_properties, "date", ["日期", "Date"])
    status_name = find_notion_property_name(data_source_properties, "status", ["状态", "Status"])
    url_name = find_notion_property_name(data_source_properties, "url", ["网址", "Website", "URL", "Link"])

    notion_title = display_youtube_title(item)
    if title_name:
        properties[title_name] = notion_title_value(notion_title or item.url or f"YouTube {item.id}")
    if note_name and note_text:
        properties[note_name] = notion_rich_text_value(note_text)
    if date_name:
        date_value = notion_date_value(item.publish_time or extra.get("publish_time") or extra.get("upload_date"))
        if date_value:
            properties[date_name] = date_value
    if status_name:
        option_name = notion_status_name(item.analysis_status or "pending", data_source_properties.get(status_name, {}).get("status", {}).get("options", []))
        if option_name:
            properties[status_name] = {"status": {"name": option_name}}
    if url_name and item.url:
        properties[url_name] = notion_url_value(item.url)
    return properties


def build_notion_x_properties(post_data: dict, data_source_properties: dict):
    body = (post_data.get("text") or "").strip()
    note_text = notion_summary_text(body, 240)
    properties = {}
    title_name = find_notion_property_name(data_source_properties, "title", ["名称", "Name", "标题"])
    note_name = find_notion_property_name(data_source_properties, "rich_text", ["备注", "Note", "Notes"])
    date_name = find_notion_property_name(data_source_properties, "date", ["日期", "Date"])
    status_name = find_notion_property_name(data_source_properties, "status", ["状态", "Status"])
    url_name = find_notion_property_name(data_source_properties, "url", ["网址", "Website", "URL", "Link"])

    notion_title = (post_data.get("kol_name") or post_data.get("kol_handle") or "X Post").strip()
    if title_name:
        properties[title_name] = notion_title_value(notion_title)
    if note_name and note_text:
        properties[note_name] = notion_rich_text_value(note_text)
    if date_name:
        date_value = notion_date_value(post_data.get("posted_at") or post_data.get("created_at"))
        if date_value:
            properties[date_name] = date_value
    if status_name:
        option_name = notion_status_name("done", data_source_properties.get(status_name, {}).get("status", {}).get("options", []))
        if option_name:
            properties[status_name] = {"status": {"name": option_name}}
    if url_name and post_data.get("url"):
        properties[url_name] = notion_url_value(post_data.get("url"))
    return properties


def generate_tags(text: str) -> str:
    if not text:
        return ""
    tags = set()
    text_lower = text.lower()
    for mapping in [ASSETS_MAP, THEMES_MAP]:
        for tag, keywords in mapping.items():
            if any(k in text_lower for k in keywords):
                tags.add(tag)
    return " ".join(sorted(tags))


def read_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def find_x_source_record(url: str):
    if not url:
        return None
    source_paths = list(Path(DATA_ROOT_DIR).glob(COLLECT_FILE_PATTERN))
    source_paths.extend(Path(UPLOAD_DIR).glob("*.json"))
    for file_path in source_paths:
        rows = read_json_file(str(file_path))
        if isinstance(rows, dict):
            rows = rows.get("items", [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and (row.get("url") or "") == url:
                return row
    return None


def hydrate_x_post_content(url: str, fallback_text: str, fallback_images=None):
    row = find_x_source_record(url)
    if not row:
        return fallback_text, list(fallback_images or [])
    text = row.get("text") or row.get("full_text") or row.get("content_raw") or fallback_text
    image_values = row.get("image_urls") or row.get("media_urls") or row.get("local_media_paths") or row.get("media_paths") or []
    images = [resolved for resolved in (resolve_image_reference(v) for v in split_possible_list(image_values)) if resolved]
    return text or fallback_text, images or list(fallback_images or [])


def read_text_file(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def get_today_filename():
    today_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DATA_ROOT_DIR, f"x_collect_{today_str}.json")


def split_csv(value):
    if not value:
        return []
    return [part for part in value.split(",") if part]


def normalize_local_media_paths(paths):
    normalized = []
    for path in paths or []:
        if path:
            normalized.append(path.replace("\\", "/"))
    return normalized


def build_image_urls(local_paths, remote_urls):
    local_urls = [f"/images/{path}" for path in normalize_local_media_paths(local_paths)]
    return local_urls or list(remote_urls or [])


def save_images_for_item(item_dict):
    media_urls = item_dict.get("media_urls", []) or []
    if not media_urls:
        item_dict["local_media_paths"] = []
        return item_dict

    today_str = datetime.now().strftime("%Y-%m-%d")
    save_dir = os.path.join(IMAGES_DIR, "auto", today_str)
    os.makedirs(save_dir, exist_ok=True)

    local_paths = []
    for url in media_urls:
        try:
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
            tweet_id = item_dict.get("id", "unknown")
            filename = f"{tweet_id}_{url_hash}.jpg"
            file_path = os.path.join(save_dir, filename)
            if not os.path.exists(file_path):
                resp = requests.get(url, timeout=12)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
            if os.path.exists(file_path):
                rel_path = os.path.relpath(file_path, DATA_ROOT_DIR).replace("\\", "/")
                local_paths.append(rel_path)
        except Exception:
            continue

    item_dict["local_media_paths"] = normalize_local_media_paths(local_paths)
    return item_dict


def remove_local_media_files(local_paths):
    deleted = []
    for rel_path in normalize_local_media_paths(local_paths):
        abs_path = os.path.normpath(os.path.join(DATA_ROOT_DIR, rel_path))
        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                deleted.append(rel_path)
        except Exception:
            continue
    return deleted


def remove_items_from_collect_files(urls):
    removed = 0
    for file_path in Path(DATA_ROOT_DIR).glob(COLLECT_FILE_PATTERN):
        items = read_json_file(str(file_path))
        if not items:
            continue
        kept = [item for item in items if (item.get("url") or "") not in urls]
        if len(kept) != len(items):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(kept, f, ensure_ascii=False, indent=2)
            removed += len(items) - len(kept)
    return removed


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def parse_payload(schema_cls):
    payload = request.get_json(silent=True) or {}
    try:
        return schema_cls(**payload), None
    except ValidationError as e:
        return None, (jsonify({"error": "validation_error", "detail": e.errors()}), 400)


def ok(data, status=200):
    return jsonify(data), status


def parse_extra(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def serialize_knowledge(item):
    local_media_paths = split_csv(item.local_media_paths)
    remote_media_paths = split_csv(item.media_paths)
    extra = parse_extra(item.extra_json)
    content_raw = item.content_raw
    content_cleaned = item.content_cleaned
    if item.source_type == "youtube" and not (content_raw or content_cleaned):
        transcript = read_text_file(extra.get("txt_path"))
        if transcript:
            content_raw = transcript
            content_cleaned = transcript
    return {
        "id": item.id,
        "source_type": item.source_type,
        "source_subtype": item.source_subtype,
        "title": item.title,
        "content_raw": content_raw,
        "content_cleaned": content_cleaned,
        "author_name": item.author_name,
        "publish_time": item.publish_time.isoformat() if item.publish_time else None,
        "url": item.url,
        "media_paths": local_media_paths or remote_media_paths,
        "local_media_paths": local_media_paths,
        "remote_media_paths": remote_media_paths,
        "tags_primary": item.tags_primary,
        "analysis_status": item.analysis_status,
        "analysis_result": item.analysis_result,
        "push_status": item.push_status,
        "notion_synced_at": extra.get("notion_synced_at"),
        "extra": extra,
    }


api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/auth/status")
def auth_status():
    return ok({
        "authenticated": has_valid_login(),
        "username": APP_USERNAME if has_valid_login() else None,
    })


@api.post("/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if username != APP_USERNAME or password != APP_PASSWORD:
        return ok({"error": "invalid_credentials"}, 401)
    session["authenticated"] = True
    session["username"] = APP_USERNAME
    return ok({"authenticated": True, "username": APP_USERNAME})


@api.post("/auth/logout")
def auth_logout():
    session.clear()
    return ok({"authenticated": False})


@api.post("/posts/bulk")
def create_posts():
    payload, err = parse_payload(KolPostList)
    if err:
        return err

    created = 0
    with db_session() as db:
        for item in payload.items:
            exists = db.query(KolPost).filter(KolPost.url == item.url).first()
            if exists:
                continue
            post = KolPost(
                kol_handle=item.kol_handle,
                kol_name=item.kol_name,
                kol_avatar_url=item.kol_avatar_url,
                posted_at=item.posted_at,
                text="",
                image_urls=",".join(item.image_urls),
                local_image_paths="",
                likes=item.likes or 0,
                retweets=item.retweets or 0,
                replies=item.replies or 0,
                url=item.url,
            )
            db.add(post)
            db.add(
                KnowledgeItem(
                    source_type="x",
                    source_subtype="tweet",
                    title=f"@{item.kol_handle}",
                    content_raw="",
                    content_cleaned="",
                    author_name=item.kol_name or item.kol_handle,
                    publish_time=item.posted_at,
                    url=item.url,
                    media_paths=",".join(item.image_urls),
                    local_media_paths="",
                    tags_primary="x",
                    analysis_status="pending",
                    source_file="auto:posts_bulk",
                    push_status="pending",
                    extra_json=json.dumps({"likes": item.likes, "retweets": item.retweets, "replies": item.replies}, ensure_ascii=False),
                )
            )
            created += 1
    return ok({"created": created})


@api.get("/posts")
def list_posts():
    kol_handle = request.args.get("kol_handle")
    limit = max(1, min(int(request.args.get("limit", 50)), 300))

    with db_session() as db:
        q = db.query(KolPost)
        if kol_handle:
            q = q.filter(KolPost.kol_handle == kol_handle)
        items = q.order_by(KolPost.id.desc()).limit(limit).all()
        urls = [item.url for item in items if item.url]
        knowledge_by_url = {}
        if urls:
            knowledge_items = db.query(KnowledgeItem).filter(
                KnowledgeItem.source_type == "x",
                KnowledgeItem.url.in_(urls),
            ).all()
            knowledge_by_url = {item.url: item for item in knowledge_items if item.url}

    result = []
    for i in items:
        fallback_images = build_image_urls(split_csv(i.local_image_paths), split_csv(i.image_urls))
        hydrated_text, hydrated_images = hydrate_x_post_content(i.url, i.text, fallback_images)
        extra = parse_extra((knowledge_by_url.get(i.url).extra_json if knowledge_by_url.get(i.url) else ""))
        result.append({
            "id": i.id,
            "kol_handle": i.kol_handle,
            "kol_name": i.kol_name,
            "kol_avatar_url": i.kol_avatar_url,
            "posted_at": i.posted_at.isoformat() if i.posted_at else None,
            "text": hydrated_text,
            "translated_text": None,
            "image_urls": hydrated_images,
            "local_image_paths": split_csv(i.local_image_paths),
            "remote_image_urls": split_csv(i.image_urls),
            "likes": i.likes,
            "retweets": i.retweets,
            "replies": i.replies,
            "url": i.url,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "notion_synced_at": extra.get("notion_synced_at"),
            "notion_page_id": extra.get("notion_page_id"),
        })
    return ok(result)


@api.post("/browse-log")
def create_browse_logs():
    payload, err = parse_payload(BrowseLogList)
    if err:
        return err
    with db_session() as db:
        for item in payload.items:
            db.add(
                BrowseLog(
                    visited_at=item.visited_at,
                    url=item.url,
                    kol_handle=item.kol_handle,
                    kol_post_url=item.kol_post_url,
                    session_id=item.session_id,
                )
            )
    return ok({"created": len(payload.items)})


@api.get("/browse-log")
def list_browse_logs():
    limit = max(1, min(int(request.args.get("limit", 100)), 500))
    with db_session() as db:
        items = db.query(BrowseLog).order_by(BrowseLog.id.desc()).limit(limit).all()
    return ok([
        {
            "id": i.id,
            "visited_at": i.visited_at.isoformat() if i.visited_at else None,
            "url": i.url,
            "kol_handle": i.kol_handle,
            "kol_post_url": i.kol_post_url,
            "session_id": i.session_id,
        }
        for i in items
    ])


@api.post("/compare/urls")
def compare_urls():
    payload, err = parse_payload(UrlComparePayload)
    if err:
        return err
    normalized = [u.strip() for u in payload.urls if u.strip()]
    result = []
    with db_session() as db:
        for url in normalized:
            match = db.query(KolPost).filter(KolPost.url == url).first()
            result.append(
                {
                    "url": url,
                    "exists": bool(match),
                    "record": {"id": match.id, "kol_handle": match.kol_handle, "text": (match.text or "")[:120]} if match else None,
                }
            )
    return ok({"total": len(normalized), "exists": [r for r in result if r["exists"]], "missing": [r for r in result if not r["exists"]], "result": result})


@api.post("/trash/batch")
def trash_batch():
    payload, err = parse_payload(TrashBatchPayload)
    if err:
        return err

    with db_session() as db:
        post_query = db.query(KolPost)
        if payload.ids:
            post_query = post_query.filter(KolPost.id.in_(payload.ids))
        if payload.urls:
            post_query = post_query.filter(KolPost.url.in_(payload.urls))
        posts = post_query.all()

        urls = {post.url for post in posts if post.url}
        if payload.urls:
            urls.update(payload.urls)

        knowledge_items = db.query(KnowledgeItem).filter(
            KnowledgeItem.source_type == "x",
            KnowledgeItem.url.in_(urls),
        ).all() if urls else []

        local_paths = []
        for post in posts:
            local_paths.extend(split_csv(post.local_image_paths))
        for item in knowledge_items:
            local_paths.extend(split_csv(item.local_media_paths))

        deleted_posts = len(posts)
        deleted_knowledge = len(knowledge_items)

        for post in posts:
            db.delete(post)
        for item in knowledge_items:
            db.delete(item)

    deleted_files = remove_local_media_files(local_paths)
    removed_collect_items = remove_items_from_collect_files(urls)
    return ok({
        "deleted": deleted_posts,
        "deleted_knowledge": deleted_knowledge,
        "deleted_images": len(deleted_files),
        "deleted_collect_items": removed_collect_items,
    })


@api.post("/push/tg")
def push_tg():
    payload, err = parse_payload(PushTgPayload)
    if err:
        return err

    with db_session() as db:
        item = db.query(KnowledgeItem).filter(KnowledgeItem.url == payload.url).first()
        if item:
            item.push_status = "pushed"
        return ok({"ok": True, "url": payload.url, "push_status": item.push_status if item else "pushed"})


@api.post("/topics/build")
def build_topic():
    payload, err = parse_payload(TopicBuildPayload)
    if err:
        return err

    with db_session() as db:
        topic = Topic(
            topic_name=payload.topic_name,
            topic_type=payload.topic_type,
            description=payload.description,
            related_item_ids=",".join(str(i) for i in payload.item_ids),
        )
        db.add(topic)
        db.flush()
        topic_id = topic.id
    return ok({"id": topic_id, "topic_name": payload.topic_name})


@api.get("/topics")
def list_topics():
    with db_session() as db:
        items = db.query(Topic).order_by(Topic.id.desc()).all()
    return ok([
        {
            "id": t.id,
            "topic_name": t.topic_name,
            "topic_type": t.topic_type,
            "description": t.description,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in items
    ])


@api.get("/topics/<int:topic_id>")
def get_topic(topic_id):
    with db_session() as db:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return ok({"error": "topic_not_found"}, 404)
        related_ids = [int(i) for i in topic.related_item_ids.split(",") if i] if topic.related_item_ids else []
        related_items = db.query(KnowledgeItem).filter(KnowledgeItem.id.in_(related_ids)).all() if related_ids else []
        result = {
            "id": topic.id,
            "topic_name": topic.topic_name,
            "topic_type": topic.topic_type,
            "description": topic.description,
            "short_term_view": topic.short_term_view,
            "mid_term_view": topic.mid_term_view,
            "long_term_view": topic.long_term_view,
            "analysis_result": topic.analysis_result,
            "related_items": [serialize_knowledge(i) for i in related_items],
        }
    return ok(result)


@api.post("/topics/<int:topic_id>/analyze")
def analyze_topic(topic_id):
    payload, err = parse_payload(TopicAnalyzePayload)
    if err:
        return err

    with db_session() as db:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return ok({"error": "topic_not_found"}, 404)
        focus = payload.focus or topic.topic_name or "topic"
        topic.short_term_view = f"Short term: attention around {focus} may keep rising."
        topic.mid_term_view = f"Mid term: {focus} needs validation from market and follow-up data."
        topic.long_term_view = f"Long term: {focus} will return to fundamentals and execution."
        topic.analysis_result = "\n".join([topic.short_term_view, topic.mid_term_view, topic.long_term_view])
    return ok({"topic_id": topic_id, "analysis_result": topic.analysis_result})


@api.get("/entities")
def list_entities():
    with db_session() as db:
        items = db.query(EntityProfile).order_by(EntityProfile.reliability_score.desc()).all()
    return ok([
        {
            "id": e.id,
            "entity_name": e.entity_name,
            "platform": e.platform,
            "recent_views": e.recent_views,
            "reliability_score": e.reliability_score,
            "forecast_score": e.forecast_score,
            "hit_cases": e.hit_cases,
            "miss_cases": e.miss_cases,
            "profile_summary": e.profile_summary,
        }
        for e in items
    ])


@api.get("/entities/<int:entity_id>")
def get_entity(entity_id):
    with db_session() as db:
        e = db.query(EntityProfile).filter(EntityProfile.id == entity_id).first()
        if not e:
            return ok({"error": "entity_not_found"}, 404)
        return ok(
            {
                "id": e.id,
                "entity_name": e.entity_name,
                "platform": e.platform,
                "recent_views": e.recent_views,
                "reliability_score": e.reliability_score,
                "forecast_score": e.forecast_score,
                "hit_cases": e.hit_cases,
                "miss_cases": e.miss_cases,
                "profile_summary": e.profile_summary,
            }
        )


@api.post("/youtube/import")
@api.post("/youtube/import/batch")
def youtube_import():
    payload, err = parse_payload(YoutubeImportPayload)
    if err:
        return err

    urls = [url.strip() for url in payload.urls if url.strip()]
    if not urls and payload.channel_name and payload.start_time:
        pipeline = YoutubePipeline()
        urls = pipeline.collect_video_urls([payload.channel_name], payload.start_time.isoformat())

    created = 0
    with db_session() as db:
        for url in urls:
            exists = db.query(KnowledgeItem).filter(
                KnowledgeItem.source_type == "youtube",
                KnowledgeItem.url == url,
            ).first()
            if exists:
                continue
            metadata = fetch_youtube_metadata(url)
            video_title = metadata["title"]
            uploader = metadata["uploader"]
            publish_time = metadata["publish_time"] or payload.start_time
            log_youtube("import_item", url=url, title=video_title, uploader=uploader, publish_time=publish_time)
            db.add(
                KnowledgeItem(
                    source_type="youtube",
                    source_subtype="subtitle",
                    title=video_title,
                    content_raw="",
                    content_cleaned="",
                    author_name=uploader or payload.channel_name,
                    publish_time=publish_time,
                    url=url,
                    tags_primary="youtube",
                    source_file="manual:youtube_import",
                    analysis_status="pending",
                    extra_json=json.dumps(
                        {
                            "channel_name": payload.channel_name,
                            "display_title": video_title,
                            "video_title": video_title,
                            "uploader": uploader,
                            "publish_time": publish_time.isoformat() if publish_time else None,
                            "upload_date": metadata["upload_date"],
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            created += 1
    return ok({"created": created, "requested": len(urls)})


@api.get("/youtube/items")
def youtube_items():
    limit = max(1, min(int(request.args.get("limit", 100)), 300))
    author_name = (request.args.get("author_name") or "").strip()
    analysis_status = (request.args.get("analysis_status") or "").strip()
    start_time_raw = (request.args.get("start_time") or "").strip()
    end_time_raw = (request.args.get("end_time") or "").strip()

    with db_session() as db:
        query = db.query(KnowledgeItem).filter(KnowledgeItem.source_type == "youtube")
        if author_name:
            query = query.filter(KnowledgeItem.author_name.ilike(f"%{author_name}%"))
        if analysis_status:
            query = query.filter(KnowledgeItem.analysis_status == analysis_status)
        if start_time_raw:
            try:
                start_time = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
                query = query.filter(KnowledgeItem.publish_time >= start_time)
            except ValueError:
                pass
        if end_time_raw:
            try:
                end_time = datetime.fromisoformat(end_time_raw.replace("Z", "+00:00"))
                query = query.filter(KnowledgeItem.publish_time <= end_time)
            except ValueError:
                pass
        items = query.order_by(KnowledgeItem.id.desc()).limit(limit).all()

    return ok([serialize_knowledge(i) for i in items])


@api.post("/youtube/analyze")
def youtube_analyze():
    payload, err = parse_payload(YoutubeAnalyzePayload)
    if err:
        return err

    log_youtube("analyze_requested", item_ids=payload.item_ids)

    with db_session() as db:
        selected = db.query(KnowledgeItem).filter(
            KnowledgeItem.source_type == "youtube",
            KnowledgeItem.id.in_(payload.item_ids),
        ).all()
        selected_data = [{"id": item.id, "url": item.url} for item in selected if item.url]
        log_youtube(
            "analyze_selected",
            selected_count=len(selected),
            selected_with_url=len(selected_data),
            selected_ids=[item.id for item in selected],
            urls=[item["url"] for item in selected_data],
        )
        for item in selected:
            item.analysis_status = "processing"

    if not selected_data:
        log_youtube("analyze_no_items", requested_ids=payload.item_ids)
        return ok({"analyzed": 0, "results": [], "reason": "no_matching_items"})

    pipeline = YoutubePipeline()
    results = pipeline.process_urls([item["url"] for item in selected_data])
    result_by_url = {row["url"]: row for row in results}
    log_youtube("analyze_pipeline_results", results=results)

    analyzed = 0
    with db_session() as db:
        items = db.query(KnowledgeItem).filter(
            KnowledgeItem.source_type == "youtube",
            KnowledgeItem.id.in_([item["id"] for item in selected_data]),
        ).all()
        for item in items:
            row = result_by_url.get(item.url, {})
            transcribe = row.get("transcribe") or {}
            transcript = ""
            txt_path = transcribe.get("txt_path")
            log_youtube(
                "analyze_item_start",
                item_id=item.id,
                url=item.url,
                downloaded=row.get("downloaded", False),
                transcribed=row.get("transcribed", False),
                txt_path=txt_path,
                transcribe_reason=transcribe.get("reason"),
            )
            if txt_path and os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    transcript = f.read().strip()
                log_youtube(
                    "analyze_item_txt_loaded",
                    item_id=item.id,
                    txt_path=txt_path,
                    transcript_length=len(transcript),
                )
            else:
                log_youtube(
                    "analyze_item_txt_missing",
                    item_id=item.id,
                    txt_path=txt_path,
                    exists=bool(txt_path and os.path.exists(txt_path)),
                )

            if row.get("downloaded") and transcribe.get("ok"):
                item.content_raw = ""
                item.content_cleaned = ""
                item.analysis_status = "done"
                derived_title = title_from_media_path(txt_path or row.get("audio_path") or "")
                if derived_title:
                    item.title = derived_title
                item.analysis_result = (
                    f"Transcript stored from {txt_path}."
                    if txt_path
                    else "Transcript stored."
                )
                extra_payload = parse_extra(item.extra_json)
                metadata = fetch_youtube_metadata(item.url) if item.url else {}
                if txt_path:
                    extra_payload["txt_path"] = txt_path
                if row.get("audio_path"):
                    extra_payload["audio_path"] = row.get("audio_path")
                if metadata.get("title"):
                    extra_payload["display_title"] = metadata["title"]
                    extra_payload["video_title"] = metadata["title"]
                    item.title = metadata["title"]
                else:
                    extra_payload["display_title"] = extra_payload.get("display_title") or item.title
                    if derived_title and not extra_payload.get("video_title"):
                        extra_payload["video_title"] = derived_title
                if metadata.get("uploader"):
                    item.author_name = metadata["uploader"]
                    extra_payload["uploader"] = metadata["uploader"]
                if metadata.get("publish_time"):
                    item.publish_time = metadata["publish_time"]
                    extra_payload["publish_time"] = metadata["publish_time"].isoformat()
                if metadata.get("upload_date"):
                    extra_payload["upload_date"] = metadata["upload_date"]
                item.extra_json = json.dumps(extra_payload, ensure_ascii=False)
                log_youtube(
                    "analyze_item_done",
                    item_id=item.id,
                    transcript_length=len(transcript),
                    cached_audio=row.get("cached_audio", False),
                    cached_transcript=transcribe.get("cached", False),
                )
            else:
                item.analysis_status = "failed"
                item.analysis_result = json.dumps(
                    {
                        "downloaded": row.get("downloaded", False),
                        "transcribed": row.get("transcribed", False),
                        "audio_path": row.get("audio_path"),
                        "txt_path": txt_path,
                        "reason": transcribe.get("reason", "download_or_transcribe_failed"),
                    },
                    ensure_ascii=False,
                )
                log_youtube(
                    "analyze_item_failed",
                    item_id=item.id,
                    analysis_result=item.analysis_result,
                )
            analyzed += 1

    log_youtube("analyze_finished", analyzed=analyzed)
    return ok({"analyzed": analyzed, "results": results})


@api.post("/youtube/<int:item_id>/transcript")
def youtube_save_transcript(item_id):
    payload = request.get_json(silent=True) or {}
    content = (payload.get("content") or "").strip()
    if not content:
        return ok({"error": "content_required"}, 400)

    with db_session() as db:
        item = db.query(KnowledgeItem).filter(
            KnowledgeItem.id == item_id,
            KnowledgeItem.source_type == "youtube",
        ).first()
        if not item:
            return ok({"error": "youtube_item_not_found"}, 404)

        extra_payload = parse_extra(item.extra_json)
        txt_path = extra_payload.get("txt_path")
        if not txt_path:
            txt_dir = Path(os.getenv("YOUTUBE_TRANSCRIBE_DIR", "./data/youtube/transcribe_output"))
            txt_dir.mkdir(parents=True, exist_ok=True)
            txt_path = str(txt_dir / f"manual_item_{item_id}.txt")

        Path(txt_path).parent.mkdir(parents=True, exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(content)

        item.content_raw = content
        item.content_raw = ""
        item.content_cleaned = ""
        item.analysis_status = "done"
        item.analysis_result = f"Transcript stored from {txt_path}."
        extra_payload["txt_path"] = txt_path
        extra_payload["display_title"] = extra_payload.get("display_title") or item.title
        extra_payload["manual_edit_at"] = datetime.utcnow().isoformat()
        extra_payload.pop("notion_synced_at", None)
        item.extra_json = json.dumps(extra_payload, ensure_ascii=False)

    log_youtube("transcript_saved", item_id=item_id, txt_path=txt_path, length=len(content))
    return ok({"saved": True, "txt_path": txt_path, "item_id": item_id})


def sync_youtube_items_to_notion(item_ids):
    log_notion("sync_start", item_ids=item_ids, data_source_id=NOTION_DATA_SOURCE_ID, database_id=NOTION_DATABASE_ID)
    try:
        data_source, notion_parent = resolve_notion_schema()
    except Exception as exc:
        log_notion("sync_schema_failed", error=str(exc))
        return {"error": "notion_sync_failed", "detail": str(exc)}, 400
    properties_schema = data_source.get("properties", {})
    log_notion("sync_schema_loaded", property_names=list(properties_schema.keys()))

    created = 0
    updated = 0
    failed = 0
    results = []

    with db_session() as db:
        items = db.query(KnowledgeItem).filter(
            KnowledgeItem.source_type == "youtube",
            KnowledgeItem.id.in_(item_ids),
        ).all()

        for item in items:
            extra_payload = parse_extra(item.extra_json)
            properties = build_notion_youtube_properties(item, properties_schema)
            if not properties:
                log_notion("sync_item_failed", item_id=item.id, reason="no_matching_notion_properties")
                failed += 1
                results.append({"item_id": item.id, "status": "failed", "reason": "no_matching_notion_properties"})
                continue

            notion_page_id = extra_payload.get("notion_page_id")
            try:
                if notion_page_id:
                    try:
                        response = notion_request("PATCH", f"/v1/pages/{notion_page_id}", {"properties": properties})
                        sync_status = "updated"
                    except Exception as exc:
                        if "archived" not in str(exc).lower():
                            raise
                        log_notion("sync_item_retry_create", item_id=item.id, old_page_id=notion_page_id, reason=str(exc))
                        response = notion_request(
                            "POST",
                            "/v1/pages",
                            {"parent": notion_parent, "properties": properties},
                        )
                        notion_page_id = response.get("id")
                        extra_payload["notion_page_id"] = notion_page_id
                        sync_status = "recreated"
                        created += 1
                    else:
                        updated += 1
                else:
                    response = notion_request(
                        "POST",
                        "/v1/pages",
                        {"parent": notion_parent, "properties": properties},
                    )
                    notion_page_id = response.get("id")
                    extra_payload["notion_page_id"] = notion_page_id
                    created += 1
                    sync_status = "created"

                extra_payload["notion_url"] = response.get("url")
                extra_payload["notion_synced_at"] = datetime.utcnow().isoformat()
                if notion_page_id:
                    try:
                        extra_payload = replace_notion_page_body(notion_page_id, item, extra_payload)
                    except Exception as exc:
                        if "archived" not in str(exc).lower():
                            raise
                        log_notion("sync_body_retry_create", item_id=item.id, old_page_id=notion_page_id, reason=str(exc))
                        response = notion_request(
                            "POST",
                            "/v1/pages",
                            {"parent": notion_parent, "properties": properties},
                        )
                        notion_page_id = response.get("id")
                        extra_payload["notion_page_id"] = notion_page_id
                        extra_payload["notion_url"] = response.get("url")
                        extra_payload = replace_notion_page_body(notion_page_id, item, extra_payload)
                        sync_status = "recreated"
                        created += 1
                item.extra_json = json.dumps(extra_payload, ensure_ascii=False)
                log_notion("sync_item_ok", item_id=item.id, status=sync_status, page_id=notion_page_id)
                results.append({"item_id": item.id, "status": sync_status, "page_id": notion_page_id})
            except Exception as exc:
                log_notion("sync_item_failed", item_id=item.id, reason=str(exc))
                failed += 1
                results.append({"item_id": item.id, "status": "failed", "reason": str(exc)})

    log_notion("sync_finished", created=created, updated=updated, failed=failed)
    return {"created": created, "updated": updated, "failed": failed, "results": results}, 200


def sync_x_post_to_notion(post_id: int = None, url: str = ""):
    log_notion("x_sync_start", post_id=post_id, url=url)
    try:
        data_source, notion_parent = resolve_notion_schema()
    except Exception as exc:
        log_notion("x_sync_schema_failed", post_id=post_id, url=url, error=str(exc))
        return {"error": "notion_sync_failed", "detail": str(exc)}, 400
    properties_schema = data_source.get("properties", {})
    log_notion("x_sync_schema_loaded", property_names=list(properties_schema.keys()))

    with db_session() as db:
        post = None
        if post_id:
            post = db.query(KolPost).filter(KolPost.id == post_id).first()
        if not post and url:
            post = db.query(KolPost).filter(KolPost.url == url).first()
        if not post:
            return {"error": "post_not_found"}, 404
        item = db.query(KnowledgeItem).filter(
            KnowledgeItem.source_type == "x",
            KnowledgeItem.url == post.url,
        ).first()
        if not item:
            return {"error": "knowledge_item_not_found"}, 404

        fallback_images = build_image_urls(split_csv(post.local_image_paths), split_csv(post.image_urls))
        hydrated_text, hydrated_images = hydrate_x_post_content(post.url, post.text or "", fallback_images)
        post_data = {
            "id": post.id,
            "kol_handle": post.kol_handle,
            "kol_name": post.kol_name,
            "posted_at": post.posted_at.isoformat() if post.posted_at else None,
            "text": hydrated_text,
            "image_urls": hydrated_images,
            "url": post.url,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
        extra_payload = parse_extra(item.extra_json)
        properties = build_notion_x_properties(post_data, properties_schema)
        if not properties:
            log_notion("x_sync_failed", post_id=post.id, url=post.url, reason="no_matching_notion_properties")
            return {"error": "notion_sync_failed", "detail": "no_matching_notion_properties"}, 400

        notion_page_id = extra_payload.get("notion_page_id")
        try:
            if notion_page_id:
                try:
                    response = notion_request("PATCH", f"/v1/pages/{notion_page_id}", {"properties": properties})
                    sync_status = "updated"
                except Exception as exc:
                    if "archived" not in str(exc).lower():
                        raise
                    log_notion("x_sync_retry_create", post_id=post.id, old_page_id=notion_page_id, reason=str(exc))
                    response = notion_request("POST", "/v1/pages", {"parent": notion_parent, "properties": properties})
                    notion_page_id = response.get("id")
                    extra_payload["notion_page_id"] = notion_page_id
                    sync_status = "recreated"
            else:
                response = notion_request("POST", "/v1/pages", {"parent": notion_parent, "properties": properties})
                notion_page_id = response.get("id")
                extra_payload["notion_page_id"] = notion_page_id
                sync_status = "created"

            extra_payload["notion_url"] = response.get("url")
            extra_payload["notion_synced_at"] = datetime.utcnow().isoformat()
            if notion_page_id:
                extra_payload = replace_notion_x_page_body(notion_page_id, post_data, extra_payload)
            item.extra_json = json.dumps(extra_payload, ensure_ascii=False)
            log_notion("x_sync_ok", post_id=post.id, status=sync_status, page_id=notion_page_id)
            return {
                "created": 1 if sync_status in {"created", "recreated"} else 0,
                "updated": 1 if sync_status == "updated" else 0,
                "failed": 0,
                "results": [{"post_id": post.id, "status": sync_status, "page_id": notion_page_id}],
            }, 200
        except Exception as exc:
            log_notion("x_sync_failed", post_id=post.id, url=post.url, reason=str(exc))
            return {
                "created": 0,
                "updated": 0,
                "failed": 1,
                "results": [{"post_id": post.id, "status": "failed", "reason": str(exc)}],
            }, 200


@api.post("/youtube/notion/sync")
def youtube_sync_notion():
    payload = request.get_json(silent=True) or {}
    item_ids = [int(item_id) for item_id in payload.get("item_ids", []) if str(item_id).strip()]

    if not item_ids:
        return ok({"error": "item_ids_required"}, 400)

    data, status = sync_youtube_items_to_notion(item_ids)
    return ok(data, status)


@api.post("/youtube/<int:item_id>/notion-sync")
def youtube_sync_single_notion(item_id):
    data, status = sync_youtube_items_to_notion([item_id])
    return ok(data, status)


@api.post("/x/notion-sync")
def x_sync_single_notion():
    payload = request.get_json(silent=True) or {}
    raw_post_id = payload.get("post_id")
    post_id = None
    if raw_post_id not in (None, "", "null"):
        try:
            post_id = int(raw_post_id)
        except (TypeError, ValueError):
            return ok({"error": "post_id_invalid"}, 400)
    url = (payload.get("url") or "").strip()
    if not post_id and not url:
        return ok({"error": "post_id_or_url_required"}, 400)
    data, status = sync_x_post_to_notion(post_id=post_id, url=url)
    return ok(data, status)


@api.get("/x/source/files")
def x_source_files():
    payload = load_x_source_payload()
    log_collect("source_files_loaded", directories=len(payload["directories"]), items=len(payload["items"]))
    return ok(payload)


@api.post("/x/source/json-upload")
def x_source_json_upload():
    files = request.files.getlist("files")
    if not files:
        return ok({"error": "files_required"}, 400)

    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    saved_files = []

    for file_storage in files:
        filename = safe_relative_path(file_storage.filename or "upload.json")
        if not filename.lower().endswith(".json"):
            continue
        dst = Path(UPLOAD_DIR) / Path(filename).name
        if dst.exists():
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            dst = Path(UPLOAD_DIR) / f"{dst.stem}_{stamp}{dst.suffix}"
        file_storage.save(dst)
        saved_files.append(str(dst))

    payload = load_x_source_payload()
    log_collect("json_upload", saved_files=saved_files, item_count=len(payload["items"]))
    return ok({"saved_files": saved_files, **payload})


@api.post("/x/source/image-folder-upload")
def x_source_image_folder_upload():
    files = request.files.getlist("files")
    relative_paths = request.form.getlist("relative_paths")
    if not files:
        return ok({"error": "files_required"}, 400)

    first_path = safe_relative_path(relative_paths[0] if relative_paths else files[0].filename or "folder")
    folder_name = Path(first_path).parts[0] if first_path else datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_root = Path(IMAGES_DIR) / folder_name
    save_root.mkdir(parents=True, exist_ok=True)

    image_map = {}
    saved_images = 0

    for index, file_storage in enumerate(files):
        relative = safe_relative_path(relative_paths[index] if index < len(relative_paths) else file_storage.filename or "")
        if not relative:
            continue
        parts = Path(relative).parts
        relative_inside = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
        target = save_root / relative_inside
        target.parent.mkdir(parents=True, exist_ok=True)
        file_storage.save(target)
        rel_url = f"/images/{folder_name}/{relative_inside.as_posix()}"
        image_map[relative_inside.as_posix()] = rel_url
        image_map[target.name] = image_map.get(target.name) or rel_url
        saved_images += 1

    log_collect("image_folder_upload", folder_name=folder_name, saved_images=saved_images)
    return ok({
        "folder_name": folder_name,
        "saved_images": saved_images,
        "image_map": image_map,
    })


@api.post("/crypto/pull")
def crypto_pull():
    payload, err = parse_payload(CryptoPullPayload)
    if err:
        return err

    extra = {
        "metric_name": payload.metric_name,
        "symbol": payload.symbol,
        "market_type": payload.market_type,
        "interval": payload.interval,
        "value": payload.value,
        "timestamp": (payload.timestamp or datetime.utcnow()).isoformat(),
    }

    with db_session() as db:
        db.add(
            KnowledgeItem(
                source_type="crypto_metric",
                source_subtype=payload.metric_name,
                title=f"{payload.symbol} {payload.metric_name}",
                content_raw=json.dumps(extra, ensure_ascii=False),
                content_cleaned=json.dumps(extra, ensure_ascii=False),
                publish_time=payload.timestamp,
                tags_primary="crypto",
                source_file="api:crypto_pull",
                analysis_status="pending",
                extra_json=json.dumps(extra, ensure_ascii=False),
            )
        )
    return ok({"status": "ok"})


@api.post("/crypto/backfill")
def crypto_backfill():
    payload, err = parse_payload(CryptoBackfillPayload)
    if err:
        return err

    created = 0
    with db_session() as db:
        for idx, value in enumerate(payload.values):
            extra = {
                "metric_name": payload.metric_name,
                "symbol": payload.symbol,
                "market_type": payload.market_type,
                "interval": payload.interval,
                "value": value,
                "index": idx,
            }
            db.add(
                KnowledgeItem(
                    source_type="crypto_metric",
                    source_subtype=payload.metric_name,
                    title=f"{payload.symbol} {payload.metric_name} #{idx + 1}",
                    content_raw=json.dumps(extra, ensure_ascii=False),
                    content_cleaned=json.dumps(extra, ensure_ascii=False),
                    publish_time=payload.start_time,
                    tags_primary="crypto",
                    source_file="api:crypto_backfill",
                    extra_json=json.dumps(extra, ensure_ascii=False),
                )
            )
            created += 1
    return ok({"created": created})


@api.get("/crypto/metrics")
def crypto_metrics():
    limit = max(1, min(int(request.args.get("limit", 100)), 300))
    with db_session() as db:
        items = db.query(KnowledgeItem).filter(KnowledgeItem.source_type == "crypto_metric").order_by(KnowledgeItem.id.desc()).limit(limit).all()
    return ok([serialize_knowledge(i) for i in items])


@api.post("/charts/capture")
def chart_capture():
    payload, err = parse_payload(ChartCapturePayload)
    if err:
        return err

    with db_session() as db:
        db.add(
            KnowledgeItem(
                source_type="chart_snapshot",
                source_subtype=payload.platform,
                title=f"{payload.platform} {payload.symbol or ''} {payload.timeframe}",
                url=payload.page_url,
                media_paths=payload.image_path,
                publish_time=datetime.utcnow(),
                tags_primary="chart",
                source_file="api:charts_capture",
                analysis_status="pending",
                extra_json=json.dumps({"timeframe": payload.timeframe, "symbol": payload.symbol}, ensure_ascii=False),
            )
        )
    return ok({"status": "captured"})


@api.post("/charts/analyze")
def chart_analyze():
    payload, err = parse_payload(ChartAnalyzePayload)
    if err:
        return err

    with db_session() as db:
        item = db.query(KnowledgeItem).filter(KnowledgeItem.id == payload.item_id).first()
        if not item:
            return ok({"error": "item_not_found"}, 404)
        item.analysis_status = "done"
        item.analysis_result = "Chart analysis finished."
    return ok({"item_id": payload.item_id, "analysis_status": "done"})


@api.get("/charts/snapshots")
def chart_snapshots():
    limit = max(1, min(int(request.args.get("limit", 100)), 300))
    with db_session() as db:
        items = db.query(KnowledgeItem).filter(KnowledgeItem.source_type == "chart_snapshot").order_by(KnowledgeItem.id.desc()).limit(limit).all()
    return ok([serialize_knowledge(i) for i in items])


@api.post("/backup/run")
def run_backup():
    payload, err = parse_payload(BackupPayload)
    if err:
        return err

    target = Path(payload.target_dir)
    target.mkdir(parents=True, exist_ok=True)
    src = Path(BASE_DIR) / "data.db"
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dst = target / f"data_{stamp}.db"
    if src.exists():
        dst.write_bytes(src.read_bytes())
    return ok({"backup": str(dst), "exists": dst.exists()})


@api.post("/database/clear")
def clear_database():
    payload, err = parse_payload(BackupPayload)
    if err:
        return err

    target = Path(payload.target_dir)
    target.mkdir(parents=True, exist_ok=True)
    src = Path(BASE_DIR) / "data.db"
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dst = target / f"data_before_clear_{stamp}.db"
    if src.exists():
        dst.write_bytes(src.read_bytes())

    with db_session() as db:
        deleted = {
            "kol_posts": db.query(KolPost).delete(),
            "browse_logs": db.query(BrowseLog).delete(),
            "knowledge_items": db.query(KnowledgeItem).delete(),
            "topics": db.query(Topic).delete(),
            "entity_profiles": db.query(EntityProfile).delete(),
        }

    db_path = Path(BASE_DIR) / "data.db"
    size_before_vacuum = db_path.stat().st_size if db_path.exists() else 0
    vacuum_ok = False
    vacuum_error = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("VACUUM")
        conn.close()
        vacuum_ok = True
    except Exception as exc:
        vacuum_error = str(exc)
    size_after_vacuum = db_path.stat().st_size if db_path.exists() else 0

    return ok({
        "backup": str(dst),
        "exists": dst.exists(),
        "deleted": deleted,
        "vacuum_ok": vacuum_ok,
        "vacuum_error": vacuum_error,
        "db_size_before_vacuum": size_before_vacuum,
        "db_size_after_vacuum": size_after_vacuum,
    })


def inject_script(html: str) -> str:
    script = """
<script>
const send=(t,p)=>parent.postMessage({type:t,payload:p},'*');
const norm=(s)=>{if(!s)return'';return s.replace(/\\s+/g,' ').trim();};
const selTweets=()=>Array.from(document.querySelectorAll('a[href*="/status/"]')).map(a=>{
  const abs=a.href;
  const m=abs.match(/https?:\\/\\/(twitter|x)\\.com\\/([^\\/]+)\\/status\\/(\\d+)/);
  const handle=m?m[2]:'';
  let article=a.closest('article');
  let text='';
  if(article){text=norm(article.innerText);}
  let avatar='';
  const img=article?article.querySelector('img[src*="twimg"]'):null;
  if(img){avatar=img.src}
  let likes=0,reposts=0,replies=0;
  Array.from(article?article.querySelectorAll('[aria-label]'):[]).forEach(el=>{
    const l=el.getAttribute('aria-label')||'';
    const n=parseInt((l.match(/\\d+/)||['0'])[0], 10);
    if(/Like/i.test(l))likes=n;
    if(/Reply/i.test(l))replies=n;
    if(/Repost|Retweet/i.test(l))reposts=n;
  });
  let imgs=[];
  Array.from(article?article.querySelectorAll('img[src*="twimg.com"]'):[]).forEach(i=>{imgs.push(i.src)});
  return {url:abs,kol_handle:handle,kol_name:handle,kol_avatar_url:avatar,text:text,image_urls:imgs,likes:likes,retweets:reposts,replies:replies};
});
const pushVisible=()=>{const items=selTweets();send('tweets_visible',{items});};
const onNav=()=>{send('browse',{url:location.href});};
const mo=new MutationObserver(()=>{pushVisible()});
mo.observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('click',e=>{const a=e.target.closest('a');if(a&&a.href.includes('/status/')){setTimeout(()=>pushVisible(),500);}});
setInterval(()=>pushVisible(),3000);
onNav();
</script>
"""
    head_inject = "<base href='/proxy/x/'><meta name='viewport' content='width=device-width, initial-scale=1'>"
    return re.sub(r"</head>", head_inject + script + "</head>", html, flags=re.IGNORECASE)


@api.post("/collect")
def collect_data():
    payload, err = parse_payload(CollectPayload)
    if err:
        return err
    header_token = request.headers.get("X-Collect-Token", "").strip()
    if payload.auth != AUTH_TOKEN and header_token != AUTH_TOKEN:
        log_collect("auth_failed", remote_addr=request.remote_addr, provided_auth=payload.auth, header_token=header_token)
        return ok({"error": "token_invalid"}, 403)
    log_collect("request_received", remote_addr=request.remote_addr, item_count=len(payload.data))

    target_file = get_today_filename()
    current_data = read_json_file(target_file)
    existing_ids = {item.get("id") for item in current_data if item.get("id")}

    created = 0
    new_items = []

    for item in payload.data:
        if item.id in existing_ids:
            log_collect("skip_duplicate_file", item_id=item.id)
            continue
        item_dict = item.model_dump()
        text = item_dict.get("full_text") or ""
        if not item_dict.get("tags"):
            item_dict["tags"] = generate_tags(text)
        item_dict = save_images_for_item(item_dict)
        item_dict["server_received_at"] = datetime.utcnow().isoformat()
        new_items.append(item_dict)
        existing_ids.add(item.id)
        created += 1

    if new_items:
        current_data.extend(new_items)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

    if new_items:
        with db_session() as db:
            for item_dict in new_items:
                handle = normalize_handle(item_dict.get("user_handle") or "unknown")
                post_url = item_dict.get("url") or f"https://x.com/{handle}/status/{item_dict.get('id')}"
                exists = db.query(KolPost).filter(KolPost.url == post_url).first()
                if exists:
                    log_collect("skip_duplicate_db", item_id=item_dict.get("id"), url=post_url)
                    continue

                posted_at = None
                if item_dict.get("created_at"):
                    try:
                        posted_at = datetime.fromisoformat(item_dict["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        posted_at = None

                remote_urls = item_dict.get("media_urls", []) or []
                local_paths = item_dict.get("local_media_paths", []) or []
                text = item_dict.get("full_text") or ""
                likes = int((item_dict.get("extra") or {}).get("likes", 0) or 0)
                retweets = int((item_dict.get("extra") or {}).get("retweets", 0) or 0)
                replies = int((item_dict.get("extra") or {}).get("replies", 0) or 0)
                name = item_dict.get("name") or handle

                post = KolPost(
                    kol_handle=handle,
                    kol_name=name,
                    kol_avatar_url="",
                    posted_at=posted_at,
                    text="",
                    image_urls=",".join(remote_urls),
                    local_image_paths=",".join(local_paths),
                    likes=likes,
                    retweets=retweets,
                    replies=replies,
                    url=post_url,
                )
                db.add(post)
                db.add(
                    KnowledgeItem(
                        source_type="x",
                        source_subtype="tweet",
                        title=f"@{handle}",
                        content_raw="",
                        content_cleaned="",
                        author_name=name,
                        publish_time=posted_at,
                        url=post_url,
                        media_paths=",".join(remote_urls),
                        local_media_paths=",".join(local_paths),
                        tags_primary="x",
                        analysis_status="pending",
                        push_status="pending",
                        source_file="collect",
                        extra_json=json.dumps({"likes": likes, "retweets": retweets, "replies": replies}, ensure_ascii=False),
                    )
                )
                log_collect(
                    "saved_item",
                    item_id=item_dict.get("id"),
                    handle=handle,
                    url=post_url,
                    media_count=len(remote_urls),
                )

    log_collect("request_finished", added=created, file=os.path.relpath(target_file, DATA_ROOT_DIR))
    return ok({"status": "success", "added": created, "file": os.path.relpath(target_file, DATA_ROOT_DIR)})


def create_app():
    app = Flask(__name__)
    app.secret_key = APP_SECRET_KEY
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    CORS(
        app,
        resources={r"/*": {"origins": [r"http://localhost:\d+", r"http://127\.0\.0\.1:\d+"]}},
        supports_credentials=True,
    )
    app.register_blueprint(api)

    @app.before_request
    def require_login():
        if request.method == "OPTIONS":
            return None
        if request.path in {"/api/auth/login", "/api/auth/status", "/api/auth/logout"}:
            return None
        if request.path == "/api/collect":
            body = request.get_json(silent=True) or {}
            header_token = request.headers.get("X-Collect-Token", "").strip()
            if body.get("auth") == AUTH_TOKEN or header_token == AUTH_TOKEN:
                return None
        protected = (
            request.path.startswith("/api/")
            or request.path.startswith("/images/")
            or request.path.startswith("/proxy/x")
        )
        if protected and not has_valid_login():
            return auth_failed_response()
        return None

    @app.get("/health")
    def health():
        return ok({"status": "ok", "framework": "flask"})

    @app.get("/images/<path:filename>")
    def get_image(filename):
        return send_from_directory(IMAGES_DIR, filename)

    @app.route("/proxy/x/<path:path>", methods=["GET"])
    @app.route("/proxy/x/", defaults={"path": "home"}, methods=["GET"])
    def proxy_x(path):
        url = f"https://twitter.com/{path}"
        q = request.args.get("q")
        params = {"q": q} if q else None
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            r = client.get(url, params=params, headers={"user-agent": "Mozilla/5.0"})
        content_type = r.headers.get("content-type", "text/html")
        if "text/html" in content_type:
            html = inject_script(r.text)
            return Response(html, mimetype="text/html", headers={"x-frame-options": "ALLOWALL"})
        return Response(r.content, mimetype=content_type)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
