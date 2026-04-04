
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
    r = client.get(f"/urls?user_id={uid}")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert all(u["user_id"] == uid for u in data)


def test_get_active_urls(client):
    _create_url(client, "https://active1.example.com")
    uid = _create_url(client, "https://todeactivate.example.com").get_json()["id"]
    client.put(f"/urls/{uid}", json={"is_active": False})
    r = client.get("/urls?is_active=true")
    assert r.status_code == 200
    data = r.get_json()
    assert all(u["is_active"] for u in data)


def test_get_inactive_urls(client):
    uid = _create_url(client, "https://inactive.example.com").get_json()["id"]
    client.put(f"/urls/{uid}", json={"is_active": False})
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
    r = client.get(f"/urls/{url_id}")
    assert r.status_code == 200
    assert r.get_json()["id"] == url_id


def test_get_nonexistent_url(client):
    r = client.get("/urls/99999")
    assert r.status_code == 404


# PUT /urls/<id>

def test_update_url_title(client):
    url_id = _create_url(client, "https://updatetitle.example.com", title="Old").get_json()["id"]
    r = client.put(f"/urls/{url_id}", json={"title": "Updated Title"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "Updated Title"


def test_deactivate_url(client):
    url_id = _create_url(client, "https://deactivate.example.com").get_json()["id"]
    r = client.put(f"/urls/{url_id}", json={"is_active": False})
    assert r.status_code == 200
    assert r.get_json()["is_active"] is False


def test_update_nonexistent_url(client):
    r = client.put("/urls/99999", json={"title": "ghost"})
    assert r.status_code == 404


# DELETE /urls/<id>

def test_delete_url(client):
    url_id = _create_url(client, "https://delete.example.com").get_json()["id"]
    r = client.delete(f"/urls/{url_id}")
    assert r.status_code == 200


def test_delete_url_removes_from_db(client):
    url_id = _create_url(client, "https://gone.example.com").get_json()["id"]
    client.delete(f"/urls/{url_id}")
    assert client.get(f"/urls/{url_id}").status_code == 404


def test_delete_nonexistent_url(client):
    r = client.delete("/urls/99999")
    assert r.status_code == 404


# Redirect via short_code

def test_redirect_via_short_code(client):
    short_code = _create_url(client, "https://redirect.example.com").get_json()["short_code"]
    r = client.get(f"/{short_code}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "https://redirect.example.com"
