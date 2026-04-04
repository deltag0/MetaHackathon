from flask import Blueprint, jsonify, request
from app.models.url import Url
from flask_login import login_required
from flask_login import login_user
from werkzeug.security import check_password_hash
import pybase62
import secrets
from datetime import datetime

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

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

@app.get("/verify-login/<token>")
def verify_login(token):
    try:
        email = verify_login_token(token)
    except SignatureExpired:
        return jsonify({"error": "Token expired"}), 400
    except BadSignature:
        return jsonify({"error": "Invalid token"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    login_user(user)
    return jsonify({"message": "Logged in successfully"}), 200

def generate_login_token(email):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt="login-salt")

def verify_login_token(token, max_age=600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.loads(token, salt="login-salt", max_age=max_age)

def send_login_email(user):
    token = generate_login_token(user.email)
    login_url = f"{BASE_URL}/verify-login/{token}"

    msg = Message(
        subject="Your login link",
        recipients=[user.email],
        body=f"Click here to log in:\n{login_url}"
    )
    mail.send(msg)

@urls_bp.post("/login")
def login():
    data = request.get_json()
    if "email" not in data:
        return jsonify({"error": "Email is required"}), 400

    user = User.get_or_none(User.email == data["email"])
    if not user:
        return jsonify({"error": "Invalid email"}), 401

    send_login_email(user)
    return jsonify({"message": "Logged in successfully"}), 200
