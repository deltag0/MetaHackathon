import csv
import os
import tempfile
from unittest.mock import patch

from app.models.url import URL


def _create_url(client, original_url="https://event-test.example.com"):
    return client.post("/urls", json={"original_url": original_url, "title": "Event Test"}).get_json()["id"]


def _create_user(client, email="eventuser@example.com"):
    return client.post("/users", json={"email": email, "username": "eventuser"}).get_json()["id"]


def _create_event(client, url_id, user_id=None, event_type="click", details=None):
    return client.post("/events", json={
        "url_id": url_id,
        "user_id": user_id,
        "event_type": event_type,
        "details": details or {},
    })


# GET /events

def test_get_events_list_empty(client):
    r = client.get("/events")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_get_events_list_returns_created(client):
    url_id = _create_url(client)
    _create_event(client, url_id)
    r = client.get("/events")
    assert r.status_code == 200
    assert len(r.get_json()) >= 1


def test_get_events_by_url(client):
    url_id1 = _create_url(client, "https://evurl1.example.com")
    url_id2 = _create_url(client, "https://evurl2.example.com")
    _create_event(client, url_id1)
    _create_event(client, url_id1)
    _create_event(client, url_id2)
    r = client.get("/events?url_id=" + str(url_id1))
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 3  # 1 auto-logged "created" + 2 manually created
    assert all(e["url_id"] == url_id1 for e in data)


def test_get_events_by_user(client):
    url_id = _create_url(client, "https://evuser.example.com")
    uid = _create_user(client, "evfilter@example.com")
    _create_event(client, url_id, user_id=uid)
    _create_event(client, url_id, user_id=uid)
    _create_event(client, url_id, user_id=None)
    r = client.get("/events?user_id=" + str(uid))
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(e["user_id"] == uid for e in data)


def test_get_events_by_type(client):
    url_id = _create_url(client, "https://evtype.example.com")
    _create_event(client, url_id, event_type="click")
    _create_event(client, url_id, event_type="click")
    _create_event(client, url_id, event_type="view")
    r = client.get("/events?event_type=click")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(e["event_type"] == "click" for e in data)


# POST /events

def test_create_event(client):
    url_id = _create_url(client, "https://create-event.example.com")
    r = _create_event(client, url_id, event_type="click", details={"referrer": "https://google.com"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["event_type"] == "click"
    assert data["url_id"] == url_id
    assert "id" in data


def test_create_event_with_user(client):
    url_id = _create_url(client, "https://ev-with-user.example.com")
    uid = _create_user(client, "evwithuser@example.com")
    r = _create_event(client, url_id, user_id=uid)
    assert r.status_code == 201
    assert r.get_json()["user_id"] == uid


def test_create_event_missing_url_id(client):
    r = client.post("/events", json={"event_type": "click"})
    assert r.status_code == 400


def test_create_event_missing_event_type(client):
    url_id = _create_url(client, "https://ev-no-type.example.com")
    r = client.post("/events", json={"url_id": url_id})
    assert r.status_code == 400


def test_create_event_stores_details(client):
    url_id = _create_url(client, "https://ev-details.example.com")
    details = {"referrer": "https://google.com", "ip": "1.2.3.4"}
    r = _create_event(client, url_id, details=details)
    assert r.status_code == 201
    assert r.get_json()["details"] == details


# GET /events — additional branch coverage

def test_list_events_returns_cached_response(client):
    with patch("app.routes.events.cache_get", return_value=[{"id": 99, "event_type": "click"}]):
        r = client.get("/events")
    assert r.status_code == 200
    assert r.get_json() == [{"id": 99, "event_type": "click"}]


def test_list_events_invalid_url_id_returns_400(client):
    r = client.get("/events?url_id=notanint")
    assert r.status_code == 400
    assert "url_id" in r.get_json()["error"]


def test_list_events_invalid_user_id_returns_400(client):
    r = client.get("/events?user_id=notanint")
    assert r.status_code == 400
    assert "user_id" in r.get_json()["error"]


def test_list_events_invalid_limit_falls_back_to_default(client):
    r = client.get("/events?limit=notanint")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# POST /events — additional validation coverage

def test_create_event_invalid_url_id_type_returns_400(client):
    r = client.post("/events", json={"url_id": "notanint", "event_type": "click"})
    assert r.status_code == 400
    assert "url_id" in r.get_json()["error"]


def test_create_event_invalid_user_id_type_returns_400(client):
    url_id = _create_url(client, "https://ev-bad-userid.example.com")
    r = client.post("/events", json={"url_id": url_id, "user_id": "notanint", "event_type": "click"})
    assert r.status_code == 400
    assert "user_id" in r.get_json()["error"]


def test_create_event_url_not_found_returns_404(client):
    r = client.post("/events", json={"url_id": 99999, "event_type": "click"})
    assert r.status_code == 404


def test_create_event_inactive_url_returns_400(client):
    url_id = _create_url(client, "https://ev-inactive-url.example.com")
    client.put("/urls/" + str(url_id), json={"is_active": False})
    r = client.post("/events", json={"url_id": url_id, "event_type": "click"})
    assert r.status_code == 400
    assert "inactive" in r.get_json()["error"]


def test_create_event_user_not_found_returns_404(client):
    url_id = _create_url(client, "https://ev-no-user.example.com")
    r = client.post("/events", json={"url_id": url_id, "user_id": 99999, "event_type": "click"})
    assert r.status_code == 404


def test_create_event_details_not_dict_returns_400(client):
    url_id = _create_url(client, "https://ev-bad-details.example.com")
    r = client.post("/events", json={"url_id": url_id, "event_type": "click", "details": "not a dict"})
    assert r.status_code == 400
    assert "details" in r.get_json()["error"]


# GET /events/<id>

def test_get_event_not_found_returns_404(client):
    r = client.get("/events/99999")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_get_event_returns_event(client):
    url_id = _create_url(client, "https://get-single-event.example.com")
    event_id = _create_event(client, url_id, event_type="click").get_json()["id"]
    r = client.get("/events/" + str(event_id))
    assert r.status_code == 200
    assert r.get_json()["id"] == event_id


# DELETE /events/<id>

def test_delete_event_not_found_returns_404(client):
    r = client.delete("/events/99999")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_delete_event_removes_event(client):
    url_id = _create_url(client, "https://del-single-event.example.com")
    event_id = _create_event(client, url_id, event_type="click").get_json()["id"]
    r = client.delete("/events/" + str(event_id))
    assert r.status_code == 200
    assert r.get_json()["message"] == "deleted"
    assert client.get("/events/" + str(event_id)).status_code == 404


# POST /events/bulk

def test_bulk_load_events_missing_file_returns_404(client):
    r = client.post("/events/bulk", json={"file": "no_such_events_file.csv"})
    assert r.status_code == 404
    assert "not found" in r.get_json()["error"]


def test_bulk_load_events_success(client):
    url_id = _create_url(client, "https://bulk-ev-load.example.com")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["url_id", "event_type", "details"])
        writer.writeheader()
        writer.writerow({"url_id": url_id, "event_type": "click", "details": '{"ip":"1.2.3.4"}'})
        tmppath = f.name

    try:
        r = client.post("/events/bulk", json={"file": tmppath})
        assert r.status_code == 201
        assert r.get_json()["count"] == 1
    finally:
        os.unlink(tmppath)


def test_bulk_load_events_invalid_details_json_inserts_with_null(client):
    url_id = _create_url(client, "https://bulk-ev-badjson.example.com")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["url_id", "event_type", "details"])
        writer.writeheader()
        writer.writerow({"url_id": url_id, "event_type": "click", "details": "{not valid json}"})
        tmppath = f.name

    try:
        r = client.post("/events/bulk", json={"file": tmppath})
        assert r.status_code == 201
    finally:
        os.unlink(tmppath)
