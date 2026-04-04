
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
    r = client.get(f"/events?url_id={url_id1}")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(e["url_id"] == url_id1 for e in data)


def test_get_events_by_user(client):
    url_id = _create_url(client, "https://evuser.example.com")
    uid = _create_user(client, "evfilter@example.com")
    _create_event(client, url_id, user_id=uid)
    _create_event(client, url_id, user_id=uid)
    _create_event(client, url_id, user_id=None)
    r = client.get(f"/events?user_id={uid}")
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
