import csv
import os
import tempfile
from unittest.mock import patch

from app.models.url import URL


def _create_url(client, original_url="https://example.com", title="Test", user_id=None):
    return client.post("/urls", json={"original_url": original_url, "title": title, "user_id": user_id})


def _make_user(client, email="urlowner@example.com"):
    return client.post("/users", json={"email": email, "username": "urlowner"}).get_json()["id"]


# GET /urls

def test_get_urls_list_empty(client):
    r = client.get("/urls")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_get_urls_list_returns_created(client):
    _create_url(client, "https://list.example.com")
    r = client.get("/urls")
    assert r.status_code == 200
    assert len(r.get_json()) >= 1


def test_get_urls_by_user(client):
    uid = _make_user(client, "filteruser@example.com")
    _create_url(client, "https://user1.example.com", user_id=uid)
    _create_url(client, "https://user2.example.com", user_id=uid)
    _create_url(client, "https://other.example.com", user_id=None)
    r = client.get("/urls?user_id=" + str(uid))
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(u["user_id"] == uid for u in data)


def test_get_active_urls(client):
    _create_url(client, "https://active1.example.com")
    uid = _create_url(client, "https://todeactivate.example.com").get_json()["id"]
    client.put("/urls/" + str(uid), json={"is_active": False})
    r = client.get("/urls?is_active=true")
    assert r.status_code == 200
    data = r.get_json()
    assert all(u["is_active"] for u in data)


def test_get_inactive_urls(client):
    uid = _create_url(client, "https://inactive.example.com").get_json()["id"]
    client.put("/urls/" + str(uid), json={"is_active": False})
    r = client.get("/urls?is_active=false")
    assert r.status_code == 200
    data = r.get_json()
    assert all(not u["is_active"] for u in data)


# POST /urls

def test_create_url(client):
    r = _create_url(client, "https://create.example.com", title="My URL")
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data
    assert "short_code" in data
    assert data["original_url"] == "https://create.example.com"
    assert data["title"] == "My URL"


def test_create_url_missing_original_url(client):
    r = client.post("/urls", json={"title": "no url"})
    assert r.status_code == 400


def test_create_url_generates_unique_short_codes(client):
    r1 = _create_url(client, "https://unique1.example.com")
    r2 = _create_url(client, "https://unique2.example.com")
    assert r1.get_json()["short_code"] != r2.get_json()["short_code"]


# GET /urls/<id>

def test_get_url_by_id(client):
    url_id = _create_url(client, "https://byid.example.com").get_json()["id"]
    r = client.get("/urls/" + str(url_id))
    assert r.status_code == 200
    assert r.get_json()["id"] == url_id


def test_get_nonexistent_url(client):
    r = client.get("/urls/99999")
    assert r.status_code == 404


# PUT /urls/<id>

def test_update_url_title(client):
    url_id = _create_url(client, "https://updatetitle.example.com", title="Old").get_json()["id"]
    r = client.put("/urls/" + str(url_id), json={"title": "Updated Title"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated Title"


def test_deactivate_url(client):
    url_id = _create_url(client, "https://deactivate.example.com").get_json()["id"]
    r = client.put("/urls/" + str(url_id), json={"is_active": False})
    assert r.status_code == 200
    assert r.get_json()["is_active"] is False


def test_update_nonexistent_url(client):
    r = client.put("/urls/99999", json={"title": "ghost"})
    assert r.status_code == 404


# DELETE /urls/<id>

def test_delete_url(client):
    url_id = _create_url(client, "https://delete.example.com").get_json()["id"]
    r = client.delete("/urls/" + str(url_id))
    assert r.status_code == 200


def test_delete_url_removes_from_db(client):
    url_id = _create_url(client, "https://gone.example.com").get_json()["id"]
    client.delete("/urls/" + str(url_id))
    assert client.get("/urls/" + str(url_id)).status_code == 404


def test_delete_nonexistent_url(client):
    r = client.delete("/urls/99999")
    assert r.status_code == 404


# Redirect via short_code

def test_redirect_via_short_code(client):
    short_code = _create_url(client, "https://redirect.example.com").get_json()["short_code"]
    r = client.get("/" + short_code, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "https://redirect.example.com"


# GET /urls — additional branch coverage

def test_list_urls_returns_cached_response(client):
    with patch("app.routes.urls.cache_get", return_value=[{"id": 42, "short_code": "abc"}]):
        r = client.get("/urls")
    assert r.status_code == 200
    assert r.get_json() == [{"id": 42, "short_code": "abc"}]


def test_list_urls_invalid_user_id_returns_400(client):
    r = client.get("/urls?user_id=notanint")
    assert r.status_code == 400
    assert "user_id" in r.get_json()["error"]


def test_list_urls_invalid_limit_falls_back_to_default(client):
    r = client.get("/urls?limit=notanint")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# GET /urls/<id> — cache hit

def test_get_url_returns_cached_response(client):
    with patch("app.routes.urls.cache_get", return_value={"id": 7, "short_code": "xyz"}):
        r = client.get("/urls/7")
    assert r.status_code == 200
    assert r.get_json()["short_code"] == "xyz"


# PUT /urls/<id> — original_url update

def test_update_url_original_url(client):
    url_id = _create_url(client, "https://before-orig.example.com").get_json()["id"]
    r = client.put("/urls/" + str(url_id), json={"original_url": "https://after-orig.example.com"})
    assert r.status_code == 200
    assert r.get_json()["original_url"] == "https://after-orig.example.com"


# POST /urls — additional branch coverage

def test_create_url_with_nonexistent_user_returns_404(client):
    r = client.post("/urls", json={"original_url": "https://badusr-url.example.com", "user_id": 99999})
    assert r.status_code == 404
    assert "user" in r.get_json()["error"]


def test_create_url_retries_on_short_code_collision(client):
    URL.create(short_code="collidex", original_url="https://pre-collision.example.com", is_active=True)

    call_count = 0

    def _mock_generate(length=7):
        nonlocal call_count
        call_count += 1
        return "collidex" if call_count == 1 else "unique99"

    with patch("app.routes.urls._generate_short_code", side_effect=_mock_generate):
        r = client.post("/urls", json={"original_url": "https://collision-url.example.com"})

    assert r.status_code == 201
    assert r.get_json()["short_code"] == "unique99"
    assert call_count >= 2


# GET /urls/<short_code>/redirect

def test_redirect_by_short_code_not_found_returns_404(client):
    r = client.get("/urls/doesnotexist999/redirect", follow_redirects=False)
    assert r.status_code == 404


def test_redirect_by_short_code_inactive_returns_410(client):
    url = _create_url(client, "https://inactive-sc-redir.example.com").get_json()
    client.put("/urls/" + str(url["id"]), json={"is_active": False})
    r = client.get("/urls/" + url["short_code"] + "/redirect", follow_redirects=False)
    assert r.status_code == 410
    assert "inactive" in r.get_json()["error"]


def test_redirect_by_short_code_active_redirects(client):
    url = _create_url(client, "https://active-sc-redir.example.com").get_json()
    r = client.get("/urls/" + url["short_code"] + "/redirect", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "https://active-sc-redir.example.com"


# POST /urls/bulk

def test_bulk_load_urls_missing_file_returns_404(client):
    r = client.post("/urls/bulk", json={"file": "no_such_urls_file.csv"})
    assert r.status_code == 404
    assert "not found" in r.get_json()["error"]


def test_bulk_load_urls_success(client):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=["short_code", "original_url", "title", "is_active"]
        )
        writer.writeheader()
        writer.writerow({
            "short_code": "bulkurlx",
            "original_url": "https://bulk-url-load.example.com",
            "title": "Bulk URL",
            "is_active": "True",
        })
        tmppath = f.name

    try:
        r = client.post("/urls/bulk", json={"file": tmppath})
        assert r.status_code == 201
        assert r.get_json()["count"] == 1
    finally:
        os.unlink(tmppath)


# URLs: _log_event exception does not crash create URL

def test_create_url_log_event_exception_is_silenced(client):
    with patch("app.routes.urls.Event.create", side_effect=Exception("db crash")):
        r = _create_url(client, "https://logevent-exc.example.com")
    assert r.status_code == 201
