from datetime import datetime

from flask import Blueprint, current_app, jsonify, redirect, request

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
            event_type="clicked",
            timestamp=datetime.utcnow(),
            details=details,
        )
        cache_delete_pattern("events:list:*")
    except Exception:
        current_app.logger.error(
            "click_event_logging_failed",
            extra={"component": "redirect", "value": str(details)},
        )
        pass


@redirect_bp.route("/<string:code>")
def follow(code):
    """Redirect to the original URL, falling back to DB if cache misses."""
    if code.endswith("+"):
        return stats(code[:-1])

    cache = get_cache()
    if cache:
        try:
            cached_url = cache.get("url:" + code)
            if cached_url:
                url = URL.get_or_none(URL.short_code == code)
                if not url or not url.is_active:
                    cache.delete(f"url:{code}")
                    return jsonify(error="Short link not found"), 404
                details = {
                    "ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "referer": request.headers.get("Referer", ""),
                }
                _log_click(url.id, details)
                return redirect(cached_url, code=302)
        except Exception:
            current_app.logger.error(
                "cache_fetch_failed",
                extra={"component": "cache", "short_code": code},
            )

    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    if cache:
        try:
            cache.set("url:" + code, url.original_url, ex=CACHE_TTL)
        except Exception:
            current_app.logger.error(
                "cache_set_failed",
                extra={"component": "cache", "short_code": code},
            )

    details = {
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "referer": request.headers.get("Referer", ""),
    }
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
