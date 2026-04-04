import csv
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.user import User

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
def list_users():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        return jsonify(error="page and per_page must be integers"), 400

    query = User.select().order_by(User.id)
    users = query.paginate(page, per_page)

    return jsonify([_user_dict(u) for u in users])


@users_bp.route("/bulk", methods=["POST"])
def bulk_users():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "users.csv")

    try:
        with open(filename, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return jsonify(error=f"{filename} not found"), 404

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
            User.insert_many(cleaned[i:i + 100]).on_conflict_ignore().execute()

    return jsonify(count=len(cleaned)), 201


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404
    return jsonify(_user_dict(user))


@users_bp.route("", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
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
    return jsonify(_user_dict(user)), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404

    data = request.get_json(silent=True) or {}
    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    user.updated_at = datetime.utcnow()
    user.save()

    return jsonify(_user_dict(user))


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="not found"), 404

    user.delete_instance()
    return jsonify(message="deleted"), 200
