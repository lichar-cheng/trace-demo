from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "data.db"
NOW = datetime(2026, 3, 12, 12, 0, 0, tzinfo=timezone.utc)

X_HANDLES = [
    ("macroalpha", "Macro Alpha"),
    ("chainpilot", "Chain Pilot"),
    ("ethsignals", "ETH Signals"),
    ("btcdepth", "BTC Depth"),
    ("solscanner", "SOL Scanner"),
    ("onchainjade", "Onchain Jade"),
    ("perpwatch", "Perp Watch"),
    ("fomowhale", "FOMO Whale"),
    ("liqmap", "Liq Map"),
    ("stableflow", "Stable Flow"),
    ("yieldframe", "Yield Frame"),
    ("riskdelta", "Risk Delta"),
]

TOPICS = [
    ("ETF Flow Rotation", "event", "Cross-market reaction to rotating ETF flows."),
    ("BTC Funding Reset", "signal", "Funding compression and short-term positioning."),
    ("ETH L2 Throughput", "theme", "Rollup activity and fee compression."),
    ("Stablecoin Mint Watch", "signal", "Minting velocity as a liquidity proxy."),
    ("Altseason False Start", "theme", "Breadth expands without durable follow-through."),
    ("Treasury Yield Shock", "macro", "Rates pressure on risk assets and leverage."),
    ("Meme Coin Exhaustion", "theme", "Attention fades while leverage remains high."),
    ("Asia Session Breakout", "event", "Repeated breakouts around the Asia open."),
]

ENTITY_NAMES = [
    "Arthur Hayes",
    "Balaji Srinivasan",
    "Cathie Wood",
    "CZ",
    "Raoul Pal",
    "Vitalik Buterin",
    "Michael Saylor",
    "Lyn Alden",
    "PlanB",
    "Willy Woo",
    "Chris Burniske",
    "Murat Pak",
    "Ansem",
    "The Kobeissi Letter",
    "Lookonchain",
    "Skew",
]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def backup_existing_db() -> Path | None:
    if not DB_PATH.exists():
        return None
    backup_path = DB_PATH.with_name(f"data.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def reset_tables(cur: sqlite3.Cursor) -> None:
    for table in ["browse_logs", "topics", "entity_profiles", "kol_posts", "knowledge_items"]:
        cur.execute(f"DELETE FROM {table}")
    try:
        for table in ["browse_logs", "topics", "entity_profiles", "kol_posts", "knowledge_items"]:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
    except sqlite3.OperationalError:
        pass


def asset_line(idx: int) -> str:
    return ["BTC", "ETH", "SOL", "Macro", "Perps", "Flows"][idx % 6]


def make_x_text(handle: str, idx: int) -> str:
    asset = ["BTC", "ETH", "SOL", "TOTAL3", "USDT.D", "DXY"][idx % 6]
    theme = [
        "spot demand is absorbing sell pressure",
        "funding has reset but open interest is rebuilding",
        "higher timeframe structure is still intact",
        "rotation into beta is visible on-chain",
        "liquidity is clustering above local highs",
        "macro prints are forcing traders to de-risk",
    ][idx % 6]
    return f"{asset} update from @{handle}: {theme}. Watch intraday reaction, ETF flows, and perp basis into the next session."


def seed_x(cur: sqlite3.Cursor) -> list[int]:
    knowledge_ids: list[int] = []
    for idx in range(180):
        handle, name = X_HANDLES[idx % len(X_HANDLES)]
        posted_at = NOW - timedelta(hours=idx * 3)
        url = f"https://x.com/{handle}/status/{1900000000000000000 + idx}"
        image_urls: list[str] = []
        if idx % 4 == 0:
            image_urls.append(f"https://picsum.photos/seed/x-{idx}/640/360")
        if idx % 10 == 0:
            image_urls.append(f"https://picsum.photos/seed/xb-{idx}/640/360")
        likes = 500 + idx * 37
        retweets = 40 + idx * 5
        replies = 12 + idx * 3
        text = make_x_text(handle, idx)
        cur.execute(
            """
            INSERT INTO kol_posts (
                kol_handle, kol_name, kol_avatar_url, posted_at, text, image_urls,
                local_image_paths, likes, retweets, replies, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                handle,
                name,
                f"https://i.pravatar.cc/150?img={(idx % 60) + 1}",
                iso(posted_at),
                text,
                ",".join(image_urls),
                "",
                likes,
                retweets,
                replies,
                url,
            ),
        )
        cur.execute(
            """
            INSERT INTO knowledge_items (
                source_type, source_subtype, title, content_raw, content_cleaned, summary,
                author_name, publish_time, url, media_paths, local_media_paths, tags_primary,
                tags_secondary, topic_ids, entity_ids, analysis_status, analysis_result,
                push_status, source_file, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "x",
                "tweet",
                f"@{handle}",
                text,
                text,
                f"{asset_line(idx)} market note from {name}.",
                name,
                iso(posted_at),
                url,
                ",".join(image_urls),
                "",
                "x market",
                "btc,eth,macro" if idx % 2 == 0 else "sol,alts,flow",
                "",
                "",
                ["pending", "done", "processing"][idx % 3],
                "Signal captured for demo view." if idx % 3 == 1 else "",
                ["pending", "pushed"][idx % 2],
                "seed:x",
                f'{{"likes": {likes}, "retweets": {retweets}, "replies": {replies}}}',
            ),
        )
        knowledge_ids.append(cur.lastrowid)
    return knowledge_ids


def seed_youtube(cur: sqlite3.Cursor) -> list[int]:
    knowledge_ids: list[int] = []
    channels = [
        "Bankless Clips",
        "Macro Desk",
        "The Rollup Room",
        "Quant Hour",
        "Asia Flow Live",
        "Derivatives Deep Dive",
    ]
    for idx in range(36):
        published = NOW - timedelta(days=idx, hours=idx % 7)
        status = ["pending", "done", "failed"][idx % 3]
        analysis_result = {
            "pending": "",
            "done": "Transcript downloaded and stored.",
            "failed": '{"downloaded": false, "transcribed": false, "reason": "demo_failure"}',
        }[status]
        channel = channels[idx % len(channels)]
        transcript = "" if status != "done" else f"Transcript excerpt for episode {idx + 1}."
        cur.execute(
            """
            INSERT INTO knowledge_items (
                source_type, source_subtype, title, content_raw, content_cleaned, summary,
                author_name, publish_time, url, media_paths, local_media_paths, tags_primary,
                tags_secondary, topic_ids, entity_ids, analysis_status, analysis_result,
                push_status, source_file, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "youtube",
                "subtitle",
                f"{channel} Episode {idx + 1}",
                transcript,
                transcript,
                f"{channel} discusses crypto market structure and liquidity rotation.",
                channel,
                iso(published),
                f"https://www.youtube.com/watch?v=demo{idx:04d}",
                "",
                "",
                "youtube",
                "",
                "",
                "",
                status,
                analysis_result,
                "pending",
                "seed:youtube",
                f'{{"channel_name": "{channel}"}}',
            ),
        )
        knowledge_ids.append(cur.lastrowid)
    return knowledge_ids


def seed_crypto(cur: sqlite3.Cursor) -> list[int]:
    knowledge_ids: list[int] = []
    metrics = ["open_interest", "funding_rate", "long_short_ratio", "basis"]
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    for idx in range(72):
        metric = metrics[idx % len(metrics)]
        symbol = symbols[idx % len(symbols)]
        value = round(1000 + idx * 13.7 + (idx % 5) * 44.2, 2)
        published = NOW - timedelta(hours=idx)
        extra_json = (
            "{"
            f'"metric_name": "{metric}", '
            f'"symbol": "{symbol}", '
            '"market_type": "future", '
            '"interval": "1h", '
            f'"value": {value}, '
            f'"timestamp": "{iso(published)}"'
            "}"
        )
        cur.execute(
            """
            INSERT INTO knowledge_items (
                source_type, source_subtype, title, content_raw, content_cleaned, summary,
                author_name, publish_time, url, media_paths, local_media_paths, tags_primary,
                tags_secondary, topic_ids, entity_ids, analysis_status, analysis_result,
                push_status, source_file, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "crypto_metric",
                metric,
                f"{symbol} {metric}",
                extra_json,
                extra_json,
                f"{symbol} {metric} snapshot for dashboard testing.",
                "",
                iso(published),
                "",
                "",
                "",
                "crypto",
                "",
                "",
                "",
                "pending",
                "",
                "pending",
                "seed:crypto",
                extra_json,
            ),
        )
        knowledge_ids.append(cur.lastrowid)
    return knowledge_ids


def seed_charts(cur: sqlite3.Cursor) -> list[int]:
    knowledge_ids: list[int] = []
    timeframes = ["15m", "1h", "4h", "1d"]
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TOTAL3"]
    for idx in range(24):
        timeframe = timeframes[idx % len(timeframes)]
        symbol = symbols[idx % len(symbols)]
        status = "done" if idx % 2 else "pending"
        cur.execute(
            """
            INSERT INTO knowledge_items (
                source_type, source_subtype, title, content_raw, content_cleaned, summary,
                author_name, publish_time, url, media_paths, local_media_paths, tags_primary,
                tags_secondary, topic_ids, entity_ids, analysis_status, analysis_result,
                push_status, source_file, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "chart_snapshot",
                "tradingview",
                f"tradingview {symbol} {timeframe}",
                "",
                "",
                f"{symbol} chart snapshot on {timeframe}.",
                "",
                iso(NOW - timedelta(hours=idx * 2)),
                f"https://www.tradingview.com/chart/demo-{idx}",
                f"data/charts/snapshots/demo_{idx:03d}.png",
                "",
                "chart",
                "",
                "",
                "",
                status,
                "Chart analysis finished." if status == "done" else "",
                "pending",
                "seed:chart",
                f'{{"timeframe": "{timeframe}", "symbol": "{symbol}"}}',
            ),
        )
        knowledge_ids.append(cur.lastrowid)
    return knowledge_ids


def seed_topics(cur: sqlite3.Cursor, related_ids: list[int]) -> None:
    for idx, (name, topic_type, description) in enumerate(TOPICS):
        chunk = related_ids[idx * 8:(idx + 1) * 8]
        short_term = f"Short term: {name} is accelerating across social and derivatives data."
        mid_term = "Mid term: confirmation depends on whether spot demand keeps pace with leverage."
        long_term = f"Long term: {name} matters only if execution and capital rotation sustain."
        cur.execute(
            """
            INSERT INTO topics (
                topic_name, topic_type, description, related_item_ids,
                short_term_view, mid_term_view, long_term_view, analysis_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                topic_type,
                description,
                ",".join(str(item_id) for item_id in chunk),
                short_term,
                mid_term,
                long_term,
                "\n".join([short_term, mid_term, long_term]),
            ),
        )


def seed_entities(cur: sqlite3.Cursor) -> None:
    for idx, entity_name in enumerate(ENTITY_NAMES):
        reliability = min(round(0.52 + (idx % 7) * 0.06, 2), 0.98)
        forecast = min(round(0.48 + (idx % 5) * 0.08, 2), 0.97)
        cur.execute(
            """
            INSERT INTO entity_profiles (
                entity_name, platform, recent_views, reliability_score,
                forecast_score, hit_cases, miss_cases, profile_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_name,
                "x",
                f"Recent view {idx + 1}: watching ETF flow, macro prints, and perp positioning.",
                reliability,
                forecast,
                8 + idx * 2,
                2 + (idx % 4),
                f"{entity_name} is included as a demo profile with varied hit-rate and narrative style.",
            ),
        )


def seed_browse_logs(cur: sqlite3.Cursor) -> None:
    for idx in range(120):
        handle, _ = X_HANDLES[idx % len(X_HANDLES)]
        cur.execute(
            """
            INSERT INTO browse_logs (visited_at, url, kol_handle, kol_post_url, session_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                iso(NOW - timedelta(minutes=idx * 9)),
                f"https://x.com/{handle}",
                handle,
                f"https://x.com/{handle}/status/{1900000000000000000 + idx}",
                f"demo-session-{1 + idx % 6}",
            ),
        )


def main() -> None:
    backup_path = backup_existing_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    reset_tables(cur)
    x_ids = seed_x(cur)
    youtube_ids = seed_youtube(cur)
    crypto_ids = seed_crypto(cur)
    chart_ids = seed_charts(cur)
    seed_topics(cur, x_ids[:40] + youtube_ids[:16] + crypto_ids[:16] + chart_ids[:16])
    seed_entities(cur)
    seed_browse_logs(cur)
    conn.commit()
    conn.close()
    print(f"Seeded demo database at {DB_PATH}")
    if backup_path:
        print(f"Backup created at {backup_path}")


if __name__ == "__main__":
    main()
