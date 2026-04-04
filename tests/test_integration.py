"""Integration tests — Flask test client + real DB."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def shorten(client, url, title=None):
    payload = {"url": url}
    if title:
        payload["title"] = title
    return client.post("/shorten", json=payload)


def register(client, email="test@example.com", password="password123"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def login(client, email="test@example.com", password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# POST /shorten — bad input
# ---------------------------------------------------------------------------

def test_shorten_missing_url(client):
    r = client.post("/shorten", json={})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_shorten_empty_url(client):
    r = client.post("/shorten", json={"url": ""})
    assert r.status_code == 400


def test_shorten_no_json_body(client):
    r = client.post("/shorten", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_shorten_no_scheme(client):
    r = shorten(client, "example.com")
    assert r.status_code == 400


def test_shorten_ftp_scheme(client):
    r = shorten(client, "ftp://example.com")
    assert r.status_code == 400


def test_shorten_javascript_scheme(client):
    r = shorten(client, "javascript:alert(1)")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /shorten — happy path
# ---------------------------------------------------------------------------

def test_shorten_creates_link(client):
    r = shorten(client, "https://example.com")
    assert r.status_code == 201
    data = r.get_json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"


def test_shorten_with_title(client):
    r = shorten(client, "https://example.com/titled", title="My Link")
    assert r.status_code == 201
    assert r.get_json()["title"] == "My Link"


# ---------------------------------------------------------------------------
# POST /shorten — uniqueness / dedup
# ---------------------------------------------------------------------------

def test_shorten_dedup_same_url_returns_same_code(client):
    r1 = shorten(client, "https://dedup.example.com")
    r2 = shorten(client, "https://dedup.example.com")
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.get_json()["short_code"] == r2.get_json()["short_code"]


def test_shorten_deleted_url_gets_new_code(client):
    r1 = shorten(client, "https://deleted.example.com")
    code = r1.get_json()["short_code"]

    client.delete(f"/api/links/{code}")

    r2 = shorten(client, "https://deleted.example.com")
    assert r2.status_code == 201
    assert r2.get_json()["short_code"] != code


# ---------------------------------------------------------------------------
# GET /<code> — redirect
# ---------------------------------------------------------------------------

def test_redirect_valid(client):
    code = shorten(client, "https://redirect.example.com").get_json()["short_code"]
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"] == "https://redirect.example.com"


def test_redirect_increments_click_count(client):
    code = shorten(client, "https://clicks.example.com").get_json()["short_code"]
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)
    r = client.get(f"/api/links/{code}")
    assert r.get_json()["click_count"] == 2


def test_redirect_nonexistent(client):
    r = client.get("/doesnotexist99", follow_redirects=False)
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_redirect_deleted_link(client):
    code = shorten(client, "https://todelete.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /<code>+ — stats
# ---------------------------------------------------------------------------

def test_stats_valid(client):
    code = shorten(client, "https://stats.example.com").get_json()["short_code"]
    r = client.get(f"/{code}+")
    assert r.status_code == 200
    data = r.get_json()
    assert data["short_code"] == code
    assert "click_count" in data


def test_stats_nonexistent(client):
    r = client.get("/nonexistent99+")
    assert r.status_code == 404


def test_stats_deleted(client):
    code = shorten(client, "https://statsdel.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.get(f"/{code}+")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/links
# ---------------------------------------------------------------------------

def test_list_links_returns_active(client):
    shorten(client, "https://list1.example.com")
    shorten(client, "https://list2.example.com")
    r = client.get("/api/links")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] >= 2


def test_list_links_excludes_deleted(client):
    code = shorten(client, "https://listdel.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.get("/api/links")
    urls = [link["short_code"] for link in r.get_json()["links"]]
    assert code not in urls


def test_list_links_pagination(client):
    for i in range(5):
        shorten(client, f"https://page{i}.example.com")
    r = client.get("/api/links?page=1&per_page=2")
    assert r.status_code == 200
    assert len(r.get_json()["links"]) <= 2


def test_list_links_invalid_page(client):
    r = client.get("/api/links?page=abc")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/links/<code>
# ---------------------------------------------------------------------------

def test_link_stats_valid(client):
    code = shorten(client, "https://detail.example.com").get_json()["short_code"]
    r = client.get(f"/api/links/{code}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["short_code"] == code
    assert "click_count" in data


def test_link_stats_nonexistent(client):
    r = client.get("/api/links/doesnotexist")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_link_stats_deleted(client):
    code = shorten(client, "https://detaildel.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.get(f"/api/links/{code}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/links/<code>
# ---------------------------------------------------------------------------

def test_update_link(client):
    code = shorten(client, "https://old.example.com").get_json()["short_code"]
    r = client.put(f"/api/links/{code}", json={"url": "https://new.example.com"})
    assert r.status_code == 200
    assert r.get_json()["original_url"] == "https://new.example.com"


def test_update_link_reflects_on_redirect(client):
    code = shorten(client, "https://before.example.com").get_json()["short_code"]
    client.put(f"/api/links/{code}", json={"url": "https://after.example.com"})
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.headers["Location"] == "https://after.example.com"


def test_update_link_invalid_url(client):
    code = shorten(client, "https://updatebad.example.com").get_json()["short_code"]
    r = client.put(f"/api/links/{code}", json={"url": "not-a-url"})
    assert r.status_code == 400


def test_update_link_nonexistent(client):
    r = client.put("/api/links/doesnotexist", json={"url": "https://example.com"})
    assert r.status_code == 404


def test_update_link_deleted(client):
    code = shorten(client, "https://updatedel.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.put(f"/api/links/{code}", json={"url": "https://example.com"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/links/<code>
# ---------------------------------------------------------------------------

def test_delete_link(client):
    code = shorten(client, "https://todel.example.com").get_json()["short_code"]
    r = client.delete(f"/api/links/{code}")
    assert r.status_code == 200


def test_delete_link_nonexistent(client):
    r = client.delete("/api/links/doesnotexist")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_delete_link_already_deleted(client):
    code = shorten(client, "https://deldel.example.com").get_json()["short_code"]
    client.delete(f"/api/links/{code}")
    r = client.delete(f"/api/links/{code}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

def test_register_success(client):
    r = register(client, "new@example.com")
    assert r.status_code == 201
    data = r.get_json()
    assert "session_token" in data
    assert data["user"]["email"] == "new@example.com"


def test_register_duplicate_email(client):
    register(client, "dup@example.com")
    r = register(client, "dup@example.com")
    assert r.status_code == 409
    assert "error" in r.get_json()


def test_register_missing_email(client):
    r = client.post("/api/auth/register", json={"password": "password123"})
    assert r.status_code == 400


def test_register_empty_email(client):
    r = client.post("/api/auth/register", json={"email": "", "password": "password123"})
    assert r.status_code == 400


def test_register_missing_password(client):
    r = client.post("/api/auth/register", json={"email": "nopass@example.com"})
    assert r.status_code == 400


def test_register_short_password(client):
    r = client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

def test_login_success(client):
    register(client, "login@example.com", "password123")
    r = login(client, "login@example.com", "password123")
    assert r.status_code == 200
    assert "session_token" in r.get_json()


def test_login_wrong_password(client):
    register(client, "wrongpass@example.com", "password123")
    r = login(client, "wrongpass@example.com", "wrongpassword")
    assert r.status_code == 401


def test_login_nonexistent_email(client):
    r = login(client, "nobody@example.com", "password123")
    assert r.status_code == 401


def test_login_missing_fields(client):
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

def test_404_returns_json(client):
    r = client.get("/this-route-does-not-exist-at-all")
    assert r.status_code == 404
    assert r.content_type == "application/json"
    assert "error" in r.get_json()


def test_405_returns_json(client):
    r = client.post("/health")
    assert r.status_code == 405
    assert r.content_type == "application/json"
    assert "error" in r.get_json()
