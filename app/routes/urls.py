from flask import Blueprint, jsonify, request
from app.models.url import Url
from flask_login import login_required
from flask_login import login_user
from werkzeug.security import check_password_hash
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

@urls_bp.post("/shorten")
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


@urls_bp.post("/login")
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.get_or_none(User.username == data["username"])
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user)
    return jsonify({"message": "Logged in successfully"}), 200

@urls_bp.post("/register")
def register():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.get_or_none(User.username == data["username"])
    if user:
        return jsonify({"error": "Username already exists"}), 400

    user = User.create(
        username=data["username"],
        password=generate_password_hash(data["password"]),
        email=data["email"],
        created_at=datetime.now()
    )

    return jsonify({"message": "User registered successfully"}), 201

