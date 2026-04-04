import csv
import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.database import db
from app.models.event import Event

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
    query = Event.select().order_by(Event.id)

    url_id = request.args.get("url_id")
    if url_id is not None:
        try:
            query = query.where(Event.url == int(url_id))
        except (ValueError, TypeError):
            return jsonify(error="url_id must be an integer"), 400

    user_id = request.args.get("user_id")
    if user_id is not None:
        try:
            query = query.where(Event.user == int(user_id))
        except (ValueError, TypeError):
            return jsonify(error="user_id must be an integer"), 400

    event_type = request.args.get("event_type")
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    return jsonify([_event_dict(e) for e in query])


@events_bp.route("/bulk", methods=["POST"])
def bulk_events():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "events.csv")

    filepath = os.path.join(_PROJECT_ROOT, filename)
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return jsonify(error=f"{filename} not found"), 404

    allowed = {"id", "url_id", "user_id", "event_type", "timestamp", "details"}
    now = str(datetime.utcnow())
    cleaned = []
    for row in rows:
        entry = {k: v for k, v in row.items() if k in allowed}
        if "details" in entry and entry["details"]:
            try:
                entry["details"] = json.loads(entry["details"])
            except (ValueError, TypeError):
                entry["details"] = None
        entry.setdefault("timestamp", now)
        cleaned.append(entry)

    with db.atomic():
        for i in range(0, len(cleaned), 100):
            Event.insert_many(cleaned[i:i + 100]).on_conflict_ignore().execute()

    return jsonify(count=len(cleaned)), 201


@events_bp.route("", methods=["POST"])
def create_event():
    data = request.get_json(silent=True) or {}
    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type", "").strip()
    details = data.get("details")

    if not url_id:
        return jsonify(error="url_id is required"), 400
    if not event_type:
        return jsonify(error="event_type is required"), 400

    event = Event.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type,
        timestamp=datetime.utcnow(),
        details=details,
    )
    return jsonify(_event_dict(event)), 201
