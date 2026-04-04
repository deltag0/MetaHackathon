import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from app.database import init_db, db, check_db_connection
from app.cache import init_cache
from app.models.user import User
from app.models.url import URL
from app.models.event import Event
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    CORS(app)

    init_db(app)
    init_cache()

    db.connect(reuse_if_open=True)
    try:
        db.create_tables([User, URL, Event], safe=True)
    except Exception:
        pass  # Tables already created by another instance
    db.close()

    register_routes(app)

    def _dependency_status():
        """Check DB and Redis. Returns (db_status, cache_status)."""
        try:
            check_db_connection()
            db_status = "ok"
        except Exception as e:
            db_status = str(e)

        from app.cache import get_cache
        cache = get_cache()
        try:
            if cache:
                cache.ping()
            cache_status = "ok"
        except Exception as e:
            cache_status = str(e)

        return db_status, cache_status

    @app.route("/health/live", methods=["GET"])
    def health_live():
        """Liveness probe — is the process alive? No external deps."""
        return jsonify(status="ok"), 200

    @app.route("/health/ready", methods=["GET"])
    def health_ready():
        """Readiness probe — are dependencies reachable?"""
        db_status, cache_status = _dependency_status()
        status_code = 200 if db_status == "ok" else 503
        return jsonify(
            status="ok" if db_status == "ok" else "degraded",
            db=db_status,
            cache=cache_status,
        ), status_code

    @app.route("/health", methods=["GET"])
    def health():
        """Backward-compatible combined health check (same as /health/ready)."""
        db_status, cache_status = _dependency_status()
        status_code = 200 if db_status == "ok" else 503
        return jsonify(
            status="ok" if db_status == "ok" else "degraded",
            db=db_status,
            cache=cache_status,
        ), status_code

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error="internal server error"), 500

    return app
