import csv
import json
import os
import secrets
from datetime import datetime

import base62
from flask import Blueprint, jsonify, redirect, request

from app.cache import cache_get, cache_set, cache_delete, cache_delete_pattern
from app.database import db
from app.models.event import Event
from app.models.url import URL
from app.models.user import User

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

urls_bp = Blueprint("urls", __name__, url_prefix="/urls")


def _log_event(url_id, user_id, event_type, details):
    try:
        Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            details=details,
        )
        cache_delete_pattern("events:list:*")
    except Exception:
        pass


def _generate_short_code(length: int = 7) -> str:
    return base62.encodebytes(secrets.token_bytes(length))[:length]


def _url_dict(u):
    return {
        "id": u.id,
        "short_code": u.short_code,
        "original_url": u.original_url,
        "title": u.title,
        "is_active": u.is_active,
        "user_id": u.user_id,
        "created_at": str(u.created_at),
        "updated_at": str(u.updated_at),
    }


@urls_bp.route("", methods=["GET"])
def list_urls():
    user_id = request.args.get("user_id")
    is_active_str = request.args.get("is_active")

    cache_key = f"urls:list:{user_id}:{is_active_str}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    query = URL.select().order_by(URL.id)

    if user_id is not None:
        try:
            query = query.where(URL.user == int(user_id))
        except (ValueError, TypeError):
            return jsonify(error="user_id must be an integer"), 400

    if is_active_str is not None:
        query = query.where(URL.is_active == (is_active_str.lower() == "true"))

    try:
        limit = int(request.args.get("limit", 100))
    except (ValueError, TypeError):
        limit = 100
    query = query.limit(min(limit, 500))

    result = [_url_dict(u) for u in query]
    cache_set(cache_key, result)
    return jsonify(result)


@urls_bp.route("/bulk", methods=["POST"])
def load_urls_csv():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "app/data/urls.csv")

    filepath = os.path.join(_PROJECT_ROOT, filename)
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return jsonify(error=f"{filename} not found"), 404

    allowed = {"id", "user_id", "short_code", "original_url", "title", "is_active", "created_at", "updated_at"}
    now = str(datetime.utcnow())
    cleaned = []
    for row in rows:
        entry = {k: v for k, v in row.items() if k in allowed}
        if "is_active" in entry:
            entry["is_active"] = entry["is_active"].strip().lower() not in ("false", "0", "")
        entry.setdefault("is_active", True)
        entry.setdefault("created_at", now)
        entry.setdefault("updated_at", now)
        cleaned.append(entry)

    with db.atomic():
        for i in range(0, len(cleaned), 100):
            URL.insert_many(cleaned[i:i + 100]).on_conflict_ignore().execute()

    db.execute_sql("SELECT setval('urls_id_seq', (SELECT MAX(id) FROM urls));")

    return jsonify(count=len(cleaned)), 201


@urls_bp.route("", methods=["POST"])
def create_url():
    data = request.get_json(silent=True) or {}
    original_url = data.get("original_url", "").strip()
    title = data.get("title", "").strip() or None
    user_id = data.get("user_id")

    if not original_url:
        return jsonify(error="original_url is required"), 400

    if user_id is not None and not User.get_or_none(User.id == user_id):
        return jsonify(error="user not found"), 404

    short_code = _generate_short_code()
    while URL.select().where(URL.short_code == short_code).exists():
        short_code = _generate_short_code()

    now = datetime.utcnow()
    url = URL.create(
        short_code=short_code,
        original_url=original_url,
        title=title,
        is_active=True,
        user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    cache_delete_pattern("urls:list:*")
    cache_set(f"url:{short_code}", json.dumps({"id": url.id, "original_url": original_url, "is_active": True}), ttl=3600)
    _log_event(url.id, user_id, "created", {})
    return jsonify(_url_dict(url)), 201


@urls_bp.route("/<short_code>/redirect", methods=["GET"])
def redirect_by_short_code(short_code):
    url = URL.get_or_none(URL.short_code == short_code)
    if not url:
        return jsonify(error="not found"), 404
    if not url.is_active:
        return jsonify(error="url is inactive"), 410
    _log_event(url.id, url.user_id, "click", {"short_code": short_code})
    return redirect(url.original_url, code=302)


@urls_bp.route("/<int:url_id>", methods=["GET"])
def get_url(url_id):
    cache_key = f"urls:{url_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="not found"), 404
    result = _url_dict(url)
    cache_set(cache_key, result)
    return jsonify(result)


@urls_bp.route("/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="not found"), 404

    data = request.get_json(silent=True) or {}
    if "title" in data:
        url.title = data["title"]
    if "original_url" in data:
        url.original_url = data["original_url"]
    if "is_active" in data:
        url.is_active = bool(data["is_active"])
    url.updated_at = datetime.utcnow()
    url.save()

    cache_delete(f"urls:{url_id}")
    cache_delete_pattern("urls:list:*")
    return jsonify(_url_dict(url))


@urls_bp.route("/<int:url_id>", methods=["DELETE"])
def delete_url(url_id):
    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="not found"), 404

    # Delete dependent events first (FK constraint)
    Event.delete().where(Event.url == url_id).execute()
    url.delete_instance()
    cache_delete(f"urls:{url_id}")
    cache_delete_pattern("urls:list:*")
    cache_delete_pattern("events:list:*")
    return jsonify(message="deleted"), 200
