import threading
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request
from peewee import SQL

from app.cache import get_cache
from app.models.event import Event
from app.models.url import URL

redirect_bp = Blueprint("redirect", __name__)

CACHE_TTL = 3600  # 1 hour


def _log_click(url_id, details):
    """Fire-and-forget click event — runs in background thread."""
    try:
        Event.create(
            url_id=url_id,
            user_id=None,
            event_type="clicked",
            timestamp=datetime.utcnow(),
            details=details,
        )
    except Exception:
        pass  # Never let analytics crash a redirect


@redirect_bp.route("/<string:code>")
def follow(code):
    if code.endswith("+"):
        return stats(code[:-1])

    # Cache-aside: check Redis first
    cache = get_cache()
    if cache:
        try:
            cached_url = cache.get(f"url:{code}")
            if cached_url:
                details = {
                    "ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "referer": request.headers.get("Referer", ""),
                }
                url = URL.get_or_none(URL.short_code == code)
                if url:
                    threading.Thread(target=_log_click, args=(url.id, details), daemon=True).start()
                return redirect(cached_url, code=302)
        except Exception:
            pass  # Redis unavailable — fall through to DB

    url = URL.get_or_none(URL.short_code == code, URL.is_active == SQL("TRUE"))
    if not url:
        return jsonify(error="Short link not found"), 404

    if not url.is_active:
        return jsonify(error="Short link is inactive"), 404

    # Populate cache
    if cache:
        try:
            cache.set(f"url:{code}", url.original_url, ex=CACHE_TTL)
        except Exception:
            pass

    details = {
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "referer": request.headers.get("Referer", ""),
    }
    threading.Thread(target=_log_click, args=(url.id, details), daemon=True).start()

    return redirect(url.original_url, code=302)


@redirect_bp.route("/<string:code>+")
def stats(code):
    url = URL.get_or_none(URL.short_code == code, URL.is_active == SQL("TRUE"))
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
