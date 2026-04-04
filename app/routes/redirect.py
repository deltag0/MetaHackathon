import json
from datetime import datetime

from flask import Blueprint, jsonify, redirect

from app.cache import get_cache, cache_delete_pattern
from app.models.event import Event
from app.models.url import URL

redirect_bp = Blueprint("redirect", __name__)

CACHE_TTL = 3600  # 1 hour


def _log_click(url):
    """Record a click event for a short link."""
    try:
        Event.create(
            url_id=url.id,
            user_id=url.user_id,
            event_type="click",
            timestamp=datetime.utcnow(),
            details={"short_code": url.short_code},
        )
        cache_delete_pattern("events:list:*")
    except Exception:
        pass


@redirect_bp.route("/s/<string:code>")
def follow(code):
    """Redirect to the original URL, falling back to DB if cache misses."""
    cache = get_cache()
    if cache:
        try:
            cached_raw = cache.get(f"url:{code}")
            if cached_raw:
                cached = json.loads(cached_raw)
                if not cached.get("is_active"):
                    return jsonify(error="link is inactive"), 410
                url = URL.get_or_none(URL.short_code == code)
                if url:
                    _log_click(url)
                return redirect(cached["original_url"], code=302)
        except Exception:
            pass

    url = URL.get_or_none(URL.short_code == code)
    if not url:
        return jsonify(error="short code not found"), 404
    if not url.is_active:
        return jsonify(error="link is inactive"), 410

    if cache:
        try:
            cache.set(f"url:{code}", json.dumps({"id": url.id, "original_url": url.original_url, "is_active": True}), ex=CACHE_TTL)
        except Exception:
            pass

    _log_click(url)
    return redirect(url.original_url, code=302)


@redirect_bp.route("/<string:code>+")
def stats(code):
    """Return basic stats for the given short code."""
    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    click_count = (
        Event.select()
        .where(Event.url == url.id, Event.event_type == "clicked")
        .count()
    )

    return jsonify(
        short_code=url.short_code,
        original_url=url.original_url,
        title=url.title,
        is_active=url.is_active,
        click_count=click_count,
        created_at=str(url.created_at),
    )
