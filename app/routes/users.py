import csv
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.cache import cache_get, cache_set, cache_delete, cache_delete_pattern
from app.database import db
from app.models.event import Event
from app.models.url import URL
from app.models.user import User

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

users_bp = Blueprint("users", __name__, url_prefix="/users")


def _user_dict(u):
    return {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "created_at": str(u.created_at),
        "updated_at": str(u.updated_at),
    }


@users_bp.route("", methods=["GET"])
def get_users_list():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        current_app.logger.warning(
            "Invalid page or per_page parameter: %s",
            request.args.get("page") or request.args.get("per_page"),
        )
        return jsonify(error="page and per_page must be integers"), 400

    cache_key = "users:list:" + str(page) + ":" + str(per_page)
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    query = User.select().order_by(User.id)
    users = query.paginate(page, per_page)
    result = [_user_dict(u) for u in users]
    cache_set(cache_key, result)

    return jsonify(result)


@users_bp.route("/bulk", methods=["POST"])
def load_users_csv():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "users.csv")

    filepath = os.path.join(_PROJECT_ROOT, filename)
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        current_app.logger.error("File not found: %s", filepath)
        return jsonify(error=filename + " not found"), 404

    allowed = {"id", "email", "username", "password_hash", "created_at", "updated_at"}
    now = str(datetime.utcnow())
    cleaned = []
    for row in rows:
        entry = {k: v for k, v in row.items() if k in allowed}
        entry.setdefault("password_hash", "")
        entry.setdefault("created_at", now)
        entry.setdefault("updated_at", now)
        cleaned.append(entry)

    with db.atomic():
        for i in range(0, len(cleaned), 100):
            User.insert_many(cleaned[i : i + 100]).on_conflict_ignore().execute()

    db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));")

    return jsonify(count=len(cleaned)), 201


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    cache_key = "users:" + str(user_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404
    result = _user_dict(user)
    cache_set(cache_key, result)
    return jsonify(result)


@users_bp.route("", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    raw_email = data.get("email", "")
    if not isinstance(raw_email, str):
        return jsonify(error="email must be a string"), 400
    email = raw_email.strip()
    username = data.get("username", "").strip() or None

    if not email:
        return jsonify(error="email is required"), 400

    if User.get_or_none(User.email == email):
        return jsonify(error="email already exists"), 409

    now = datetime.utcnow()
    user = User.create(
        email=email,
        username=username,
        password_hash=data.get("password_hash", ""),
        created_at=now,
        updated_at=now,
    )
    cache_delete_pattern("users:list:*")
    return jsonify(_user_dict(user)), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404

    data = request.get_json(silent=True) or {}
    if "email" in data:
        new_email = data["email"]
        existing = User.get_or_none(User.email == new_email)
        if existing and existing.id != user_id:
            return jsonify(error="email already exists"), 409
        user.email = new_email
    if "username" in data:
        user.username = data["username"]
    user.updated_at = datetime.utcnow()
    user.save()

    cache_delete("users:" + str(user_id))
    cache_delete_pattern("users:list:*")
    return jsonify(_user_dict(user))


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404

    # Delete all events for URLs owned by this user (Event.url FK is NOT NULL)
    user_url_ids = URL.select(URL.id).where(URL.user == user_id)
    Event.delete().where(Event.url.in_(user_url_ids)).execute()
    # Delete events directly linked to this user on other URLs
    Event.delete().where(Event.user == user_id).execute()
    # Now safe to delete URLs and user
    URL.delete().where(URL.user == user_id).execute()
    user.delete_instance()
    cache_delete("users:" + str(user_id))
    cache_delete_pattern("users:list:*")
    cache_delete_pattern("urls:list:*")
    cache_delete_pattern("events:list:*")
    return jsonify(message="deleted"), 200
