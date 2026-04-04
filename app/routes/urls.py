import secrets
from datetime import datetime

import base62
from flask import Blueprint, jsonify, request

from app.models.url import URL

urls_bp = Blueprint("urls", __name__, url_prefix="/urls")


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
    query = URL.select().order_by(URL.id)

    user_id = request.args.get("user_id")
    if user_id is not None:
        try:
            query = query.where(URL.user == int(user_id))
        except (ValueError, TypeError):
            return jsonify(error="user_id must be an integer"), 400

    is_active_str = request.args.get("is_active")
    if is_active_str is not None:
        query = query.where(URL.is_active == (is_active_str.lower() == "true"))

    return jsonify([_url_dict(u) for u in query])


@urls_bp.route("", methods=["POST"])
def create_url():
    data = request.get_json(silent=True) or {}
    original_url = data.get("original_url", "").strip()
    title = data.get("title", "").strip() or None
    user_id = data.get("user_id")

    if not original_url:
        return jsonify(error="original_url is required"), 400

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
    return jsonify(_url_dict(url)), 201


@urls_bp.route("/<int:url_id>", methods=["GET"])
def get_url(url_id):
    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="not found"), 404
    return jsonify(_url_dict(url))


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

    return jsonify(_url_dict(url))


@urls_bp.route("/<int:url_id>", methods=["DELETE"])
def delete_url(url_id):
    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="not found"), 404

    url.delete_instance()
    return jsonify(message="deleted"), 200
