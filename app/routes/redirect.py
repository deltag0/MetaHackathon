import json
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request

from app.cache import get_cache, cache_delete_pattern
from app.models.event import Event
from app.models.url import URL

redirect_bp = Blueprint("redirect", __name__)

CACHE_TTL = 3600  # 1 hour


def _log_click(url_id, details):
    """Record a click event for a short link in the background."""
    try:
        Event.create(
            url_id=url_id,
            user_id=None,
            event_type="click",
            timestamp=datetime.utcnow(),
            details=details,
        )
        cache_delete_pattern("events:list:*")
    except Exception:
        pass


@redirect_bp.route("/<string:code>")
def follow(code):
    """Redirect to the original URL, falling back to DB if cache misses."""
    if code.endswith("+"):
        return stats(code[:-1])

    details = {
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "referer": request.headers.get("Referer", ""),
    }

    cache = get_cache()
    if cache:
        try:
            cached_raw = cache.get(f"url:{code}")
            if cached_raw:
                cached = json.loads(cached_raw)
                if not cached.get("is_active"):
                    cache.delete(f"url:{code}")
                    return jsonify(error="Short link not found"), 404
                _log_click(cached["id"], details)
                return redirect(cached["original_url"], code=302)
        except Exception:
            pass

    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    if cache:
        try:
            cache.set(f"url:{code}", json.dumps({"id": url.id, "original_url": url.original_url, "is_active": True}), ex=CACHE_TTL)
        except Exception:
            pass

    _log_click(url.id, details)
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
