#!/usr/bin/env python3
# Last Edited: 2026-03-12
"""独立 YouTube 流水线入口（与 Flask 主服务解耦）。"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from services.youtube import YoutubePipeline, default_channel_ids  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="YouTube pipeline runner")
    parser.add_argument("--start-date", required=True, help="RFC3339, e.g. 2026-02-27T00:00:00Z")
    parser.add_argument("--channel-id", action="append", default=[], help="repeatable channel id")
    parser.add_argument("--urls-file", help="newline url file")
    parser.add_argument("--output", default="data/youtube/pipeline_result.json", help="result file path")
    args = parser.parse_args()

    pipeline = YoutubePipeline()

    urls = []
    if args.urls_file:
        lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        urls.extend([x.strip() for x in lines if x.strip()])
    else:
        channels = args.channel_id or default_channel_ids()
        urls = pipeline.collect_video_urls(channels, args.start_date)

    results = pipeline.process_urls(urls)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"processed={len(results)} output={out}")


if __name__ == "__main__":
    main()
