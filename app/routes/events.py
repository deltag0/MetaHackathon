from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.event import Event

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
