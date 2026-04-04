import os
import json
import uuid
import logging
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, g, request
from flask_cors import CORS

from app.database import init_db, db, check_db_connection
from app.cache import init_cache
from app.models.user import User
from app.models.url import URL
from app.models.event import Event
from app.routes import register_routes


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "service": "url-shortener-api",
        }

        # Allow route and dependency logs to attach machine-readable fields.
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "component",
            "error",
            "user_id",
            "url_id",
            "short_code",
            "param",
            "value",
            "resource",
            "reason",
            "log_level",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, ensure_ascii=True)


def _configure_logging(app: Flask) -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = JsonFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(handler)
    werkzeug_logger.setLevel(level)
    werkzeug_logger.propagate = False

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
        current_app.logger.warning(
            "db_create_tables_skipped",
            extra={"component": "db", "reason": "tables_already_exist_or_race"},
        )
        pass  # Tables already created by another instance
    db.close()

    register_routes(app)

    @app.before_request
    def _before_request_log_start():
        g.request_start = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _after_request_log(response):
        start = getattr(g, "request_start", None)
        elapsed_ms = (time.perf_counter() - start) * 1000 if start else 0
        app.logger.info(
            "request_completed",
            extra={
                "request_id": getattr(g, "request_id", ""),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        return response

    def _dependency_status():
        """Check DB and Redis. Returns (db_status, cache_status)."""
        try:
            check_db_connection()
            db_status = "ok"
        except Exception as e:
            current_app.logger.error(
                "dependency_check_failed",
                extra={"component": "db", "error": str(e)},
            )
            db_status = str(e)

        from app.cache import get_cache
        cache = get_cache()
        try:
            if cache:
                cache.ping()
            cache_status = "ok"
        except Exception as e:
            current_app.logger.error(
                "dependency_check_failed",
                extra={"component": "cache", "error": str(e)},
            )
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
        app.logger.warning(
            "http_not_found",
            extra={
                "request_id": getattr(g, "request_id", ""),
                "method": request.method,
                "path": request.path,
                "status_code": 404,
            },
        )
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        app.logger.warning(
            "http_method_not_allowed",
            extra={
                "request_id": getattr(g, "request_id", ""),
                "method": request.method,
                "path": request.path,
                "status_code": 405,
            },
        )
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception(
            "http_internal_error",
            extra={
                "request_id": getattr(g, "request_id", ""),
                "method": request.method,
                "path": request.path,
                "status_code": 500,
            },
        )
        return jsonify(error="internal server error"), 500

    return app
