from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _make_session_token(user_id: int) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(user_id, salt="session")


def _verify_session_token(token: str) -> int | None:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        return s.loads(token, salt="session", max_age=SESSION_MAX_AGE)
    except (SignatureExpired, BadSignature):
        return None


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email:
        return jsonify(error="email is required"), 400
    if not password:
        return jsonify(error="password is required"), 400
    if len(password) < 8:
        return jsonify(error="password must be at least 8 characters"), 400

    if User.get_or_none(User.email == email):
        return jsonify(error="email already registered"), 409

    user = User.create(
        email=email,
        password_hash=generate_password_hash(password),
        created_at=datetime.utcnow(),
    )

    current_app.logger.info("Registered user %s", email)

    return jsonify(
        session_token=_make_session_token(user.id),
        user={"id": user.id, "email": user.email},
    ), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    user = User.get_or_none(User.email == email)
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="invalid email or password"), 401

    return jsonify(
        session_token=_make_session_token(user.id),
        user={"id": user.id, "email": user.email},
    )
