import secrets
from datetime import datetime
from urllib.parse import urlparse

import base62
from flask import Blueprint, jsonify, request

from app.cache import get_cache
from app.models.event import Event
from app.models.url import URL

links_bp = Blueprint("links", __name__)


def _generate_short_code(length: int = 7) -> str:
    return base62.encodebytes(secrets.token_bytes(length))[:length]


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _log_event(url_id, user_id, event_type, details):
    try:
        Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            details=details,
        )
    except Exception:
        pass


@links_bp.route("/shorten", methods=["POST"])
def shorten():
    """Create a short link for the given URL, or return the existing one."""
    data = request.get_json(silent=True) or {}
    original_url = data.get("url", "").strip()
    title = data.get("title", "").strip() or None
    user_id = data.get("user_id")

    if not original_url:
        return jsonify(error="url is required"), 400
    if not _valid_url(original_url):
        return jsonify(error="url must start with http:// or https://"), 400

    existing = URL.get_or_none(URL.original_url == original_url, URL.user == user_id, URL.is_active)
    if existing:
        return jsonify(
            short_code=existing.short_code,
            short_url=f"{request.host_url}{existing.short_code}",
            original_url=existing.original_url,
            title=existing.title,
        )

    short_code = _generate_short_code()

    # ! should add measure to prevent infinite loop
    while URL.select().where(URL.short_code == short_code).exists():
        short_code = _generate_short_code()

    url = URL.create(
        short_code=short_code,
        original_url=original_url,
        title=title,
        is_active=True,
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _log_event(url.id, user_id, "created", {"short_code": short_code, "original_url": original_url})

    return jsonify(
        short_code=short_code,
        short_url=f"{request.host_url}{short_code}",
        original_url=original_url,
        title=title,
    ), 201


@links_bp.route("/api/links", methods=["GET"])
def list_links():
    """Return a paginated list of active short links."""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        return jsonify(error="page and per_page must be integers"), 400

    query = URL.select().where(URL.is_active).order_by(URL.created_at.desc())
    total = query.count()
    urls = query.paginate(page, per_page)

    return jsonify(
        total=total,
        page=page,
        per_page=per_page,
        links=[
            {
                "short_code": u.short_code,
                "original_url": u.original_url,
                "title": u.title,
                "created_at": str(u.created_at),
            }
            for u in urls
        ],
    )


@links_bp.route("/api/links/<string:code>", methods=["GET"])
def link_stats(code):
    """Return stats and recent events for a single short link."""
    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    click_count = Event.select().where(Event.url == url.id, Event.event_type == "clicked").count()
    events = (
        Event.select()
        .where(Event.url == url.id)
        .order_by(Event.timestamp.desc())
        .limit(50)
    )

    return jsonify(
        short_code=url.short_code,
        original_url=url.original_url,
        title=url.title,
        is_active=url.is_active,
        click_count=click_count,
        created_at=str(url.created_at),
        updated_at=str(url.updated_at),
        recent_events=[
            {"type": e.event_type, "timestamp": str(e.timestamp), "details": e.details}
            for e in events
        ],
    )


@links_bp.route("/api/links/<string:code>", methods=["PUT"])
def update_link(code):
    """Update the URL or title of an existing short link."""
    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    data = request.get_json(silent=True) or {}
    new_url = data.get("url", "").strip() or None
    new_title = data.get("title", "").strip() or None

    if new_url and not _valid_url(new_url):
        return jsonify(error="url must start with http:// or https://"), 400

    old_url = url.original_url
    if new_url:
        url.original_url = new_url
    if new_title:
        url.title = new_title
    url.updated_at = datetime.utcnow()
    url.save()

    cache = get_cache()
    if cache:
        try:
            cache.delete(f"url:{code}")
        except Exception:
            pass

    _log_event(url.id, None, "updated", {"old_url": old_url, "new_url": url.original_url})

    return jsonify(
        short_code=url.short_code,
        original_url=url.original_url,
        title=url.title,
        updated_at=str(url.updated_at),
    )


@links_bp.route("/api/links/<string:code>", methods=["DELETE"])
def delete_link(code):
    """Soft-delete a short link by marking it inactive."""
    url = URL.get_or_none(URL.short_code == code, URL.is_active)
    if not url:
        return jsonify(error="Short link not found"), 404

    url.is_active = False
    url.updated_at = datetime.utcnow()
    url.save()

    cache = get_cache()
    if cache:
        try:
            cache.delete(f"url:{code}")
        except Exception:

            pass

    _log_event(url.id, None, "deleted", {"short_code": code})

    return jsonify(message="deleted")
