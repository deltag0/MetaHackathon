import csv
import json
import os
from datetime import datetime

from flask import current_app, Blueprint, jsonify, request

from app.cache import cache_get, cache_set, cache_delete_pattern
from app.database import db
from app.models.event import Event
from app.models.url import URL
from app.models.user import User

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

events_bp = Blueprint("events", __name__, url_prefix="/events")


def _event_dict(e):
    return {
        "id": e.id,
        "url_id": e.url_id,
        "user_id": e.user_id,
        "event_type": e.event_type,
        "timestamp": str(e.timestamp),
        "details": e.details,
    }


@events_bp.route("", methods=["GET"])
def list_events():
    url_id = request.args.get("url_id")
    user_id = request.args.get("user_id")
    event_type = request.args.get("event_type")

    cache_key = "events:list:" + str(url_id) + ":" + str(user_id) + ":" + str(event_type)
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    query = Event.select().order_by(Event.id)

    if url_id is not None:
        try:
            query = query.where(Event.url == int(url_id))
        except (ValueError, TypeError):
            current_app.logger.warning(
                "invalid_filter",
                extra={"component": "events", "param": "url_id", "value": str(url_id)},
            )
            return jsonify(error="url_id must be an integer"), 400

    if user_id is not None:
        try:
            query = query.where(Event.user == int(user_id))
        except (ValueError, TypeError):
            current_app.logger.warning(
                "invalid_filter",
                extra={"component": "events", "param": "user_id", "value": str(user_id)},
            )
            return jsonify(error="user_id must be an integer"), 400

    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    try:
        limit = int(request.args.get("limit", 100))
    except (ValueError, TypeError):
        current_app.logger.warning(
            "invalid_limit_parameter",
            extra={"component": "events", "param": "limit", "value": str(request.args.get("limit"))},
        )
        limit = 100
    query = query.limit(min(limit, 500))

    result = [_event_dict(e) for e in query]
    cache_set(cache_key, result, ttl=60)
    return jsonify(result)


@events_bp.route("/bulk", methods=["POST"])
def load_events_csv():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "events.csv")

    filepath = os.path.join(_PROJECT_ROOT, filename)
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        current_app.logger.error(
            "file_not_found",
            extra={"component": "events", "resource": filepath},
        )
        return jsonify(error=filename + " not found"), 404

    allowed = {"id", "url_id", "user_id", "event_type", "timestamp", "details"}
    now = str(datetime.utcnow())
    cleaned = []
    for row in rows:
        entry = {k: v for k, v in row.items() if k in allowed}
        if "details" in entry and entry["details"]:
            try:
                entry["details"] = json.loads(entry["details"])
            except (ValueError, TypeError):
                current_app.logger.warning(
                    "invalid_event_details_format",
                    extra={"component": "events", "value": str(row)},
                )
                entry["details"] = None
        entry.setdefault("timestamp", now)
        cleaned.append(entry)

    with db.atomic():
        for i in range(0, len(cleaned), 100):
            Event.insert_many(cleaned[i:i + 100]).on_conflict_ignore().execute()

    db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events));")

    return jsonify(count=len(cleaned)), 201


@events_bp.route("", methods=["POST"])
def create_event():
    data = request.get_json(silent=True) or {}
    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type", "")
    if isinstance(event_type, str):
        event_type = event_type.strip()
    details = data.get("details")

    if url_id is None:
        return jsonify(error="url_id is required"), 400
    try:
        url_id = int(url_id)
    except (ValueError, TypeError):
        return jsonify(error="url_id must be an integer"), 400
    if not event_type:
        return jsonify(error="event_type is required"), 400

    if user_id is not None:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify(error="user_id must be an integer"), 400

    url = URL.get_or_none(URL.id == url_id)
    if not url:
        return jsonify(error="url not found"), 404
    if not url.is_active:
        return jsonify(error="url is inactive"), 400

    if user_id is not None and not User.get_or_none(User.id == user_id):
        return jsonify(error="user not found"), 404

    if details is not None and not isinstance(details, dict):
        return jsonify(error="details must be a JSON object"), 400

    event = Event.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type,
        timestamp=datetime.utcnow(),
        details=details,
    )
    cache_delete_pattern("events:list:*")
    return jsonify(_event_dict(event)), 201


@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event:
        return jsonify(error="not found"), 404
    return jsonify(_event_dict(event))


@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event:
        return jsonify(error="not found"), 404

    event.delete_instance()
    cache_delete_pattern("events:list:*")
    return jsonify(message="deleted"), 200
