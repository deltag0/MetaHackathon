import os
import logging
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, g, request
from flask_cors import CORS

from app.database import init_db, db, check_db_connection
from app.cache import init_cache
from app.models.user import User
from app.models.url import URL
from app.models.event import Event
from app.routes import register_routes


def _configure_logging(app: Flask) -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False

    logging.getLogger("werkzeug").setLevel(level)
    app.logger.info("Logger configured", extra={"log_level": level_name})


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    CORS(app)
    _configure_logging(app)

    init_db(app)
    init_cache()

    db.connect(reuse_if_open=True)
    try:
        db.create_tables([User, URL, Event], safe=True)
    except Exception:
        pass  # Tables already created by another instance
    db.close()

    register_routes(app)

    @app.before_request
    def _before_request_log_start():
        g.request_start = time.perf_counter()

    @app.after_request
    def _after_request_log(response):
        start = getattr(g, "request_start", None)
        elapsed_ms = (time.perf_counter() - start) * 1000 if start else 0
        app.logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response

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
        app.logger.warning("404 %s", request.path)
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        app.logger.warning("405 %s %s", request.method, request.path)
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("500 %s", request.path)
        return jsonify(error="internal server error"), 500

    return app
