# Last Edited: 2026-03-12
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import httpx
from flask import Blueprint, Flask, Response, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

BASE_DIR = os.path.dirname(__file__)

from models import SessionLocal, KolPost, BrowseLog, KnowledgeItem, Topic, EntityProfile, init_db
from schemas import (
    KolPostList,
    BrowseLogList,
    UrlComparePayload,
    TrashBatchPayload,
    PushTgPayload,
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

init_db()


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
    return {
        "id": item.id,
        "source_type": item.source_type,
        "source_subtype": item.source_subtype,
        "title": item.title,
        "content_raw": item.content_raw,
        "content_cleaned": item.content_cleaned,
        "author_name": item.author_name,
        "publish_time": item.publish_time.isoformat() if item.publish_time else None,
        "url": item.url,
        "media_paths": (item.media_paths or "").split(",") if item.media_paths else [],
        "tags_primary": item.tags_primary,
        "analysis_status": item.analysis_status,
        "analysis_result": item.analysis_result,
        "push_status": item.push_status,
        "extra": parse_extra(item.extra_json),
    }


api = Blueprint("api", __name__, url_prefix="/api")


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
                text=item.text,
                image_urls=",".join(item.image_urls),
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
                    content_raw=item.text,
                    content_cleaned=item.text,
                    author_name=item.kol_name or item.kol_handle,
                    publish_time=item.posted_at,
                    url=item.url,
                    media_paths=",".join(item.image_urls),
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

    return ok([
        {
            "id": i.id,
            "kol_handle": i.kol_handle,
            "kol_name": i.kol_name,
            "kol_avatar_url": i.kol_avatar_url,
            "posted_at": i.posted_at.isoformat() if i.posted_at else None,
            "text": i.text,
            "translated_text": None,
            "image_urls": i.image_urls.split(",") if i.image_urls else [],
            "likes": i.likes,
            "retweets": i.retweets,
            "replies": i.replies,
            "url": i.url,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in items
    ])


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
        deleted_posts = 0
        if payload.ids:
            deleted_posts += db.query(KolPost).filter(KolPost.id.in_(payload.ids)).delete(synchronize_session=False)
        if payload.urls:
            deleted_posts += db.query(KolPost).filter(KolPost.url.in_(payload.urls)).delete(synchronize_session=False)
            db.query(KnowledgeItem).filter(KnowledgeItem.url.in_(payload.urls)).delete(synchronize_session=False)
    return ok({"deleted": deleted_posts})


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
        focus = payload.focus or topic.topic_name or "事件"
        topic.short_term_view = f"短期：{focus}热度提升，观点分歧明显。"
        topic.mid_term_view = f"中期：{focus}进入验证阶段，信息噪声下降。"
        topic.long_term_view = f"长期：{focus}将回归基本面与执行结果。"
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

    created = 0
    with db_session() as db:
        for url in payload.urls:
            db.add(
                KnowledgeItem(
                    source_type="youtube",
                    source_subtype="subtitle",
                    title=f"YouTube: {url}",
                    content_raw="字幕原文（待抓取）",
                    content_cleaned="",
                    author_name=payload.channel_name,
                    publish_time=payload.start_time,
                    url=url,
                    tags_primary="youtube",
                    source_file="manual:youtube_import",
                    analysis_status="pending",
                    extra_json=json.dumps({"channel_name": payload.channel_name}, ensure_ascii=False),
                )
            )
            created += 1
    return ok({"created": created})


@api.get("/youtube/items")
def youtube_items():
    limit = max(1, min(int(request.args.get("limit", 100)), 300))
    with db_session() as db:
        items = db.query(KnowledgeItem).filter(KnowledgeItem.source_type == "youtube").order_by(KnowledgeItem.id.desc()).limit(limit).all()
    return ok([serialize_knowledge(i) for i in items])


@api.post("/youtube/analyze")
def youtube_analyze():
    payload, err = parse_payload(YoutubeAnalyzePayload)
    if err:
        return err

    with db_session() as db:
        items = db.query(KnowledgeItem).filter(KnowledgeItem.id.in_(payload.item_ids)).all()
        for item in items:
            item.analysis_status = "done"
            item.content_cleaned = "去口语化整理完成"
            item.analysis_result = "观点总结：该视频强调多模态模型将成为行业主线。"
    return ok({"analyzed": len(items)})


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
        item.analysis_result = "图表分析：趋势偏强，短线可能回踩后继续上行。"
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


def inject_script(html: str) -> str:
    script = """
<script>
const send=(t,p)=>parent.postMessage({type:t,payload:p},'*');
const norm=(s)=>{if(!s)return'';return s.replace(/\s+/g,' ').trim();};
const selTweets=()=>Array.from(document.querySelectorAll('a[href*="/status/"]')).map(a=>{
  const abs=a.href;
  const m=abs.match(/https?:\/\/twitter\.com\/([^\/]+)\/status\/(\d+)/);
  const handle=m?m[1]:'';
  let article=a.closest('article');
  let text='';
  if(article){text=norm(article.innerText);}
  let avatar='';
  const img=article?article.querySelector('img[src*="twimg"]'):null;
  if(img){avatar=img.src}
  let likes=0,reposts=0,replies=0;
  Array.from(article?article.querySelectorAll('[aria-label]'):[]).forEach(el=>{
    const l=el.getAttribute('aria-label')||'';
    const n=parseInt((l.match(/\d+/)||['0'])[0]);
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


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.register_blueprint(api)

    @app.get("/health")
    def health():
        return ok({"status": "ok", "framework": "flask"})

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
