from flask import Blueprint, jsonify, request
from app.models.url import Url
from flask_login import login_required
import pybase62
import secrets
from datetime import datetime

urls_bp = Blueprint("urls", __name__, url_prefix="/api")


@urls_bp.get("/")
def get_urls():
    return jsonify({"message": "List of shortened URLs"}), 200

def generate_short_code(length=7):
    random_bytes = secrets.token_bytes(length)
    return pybase62.encodebytes(random_bytes)[:length]

@urls_bp.post("/")
@login_required
def create_short_url():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400
    if "title" not in data:
        return jsonify({"error": "Title is required"}), 400

    short_code = generate_short_code()
    while Url.select().where(Url.short_code == short_code).exists():
        short_code = generate_short_code()

    url = Url.create(
        user_id=current_user.id,
        original_url=data["url"],
        short_code=short_code,
        title=data["title"],
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    return jsonify({
        "message": "URL shortened successfully",
        "short_code": short_code,
        "original_url": data["url"]
    }), 201
