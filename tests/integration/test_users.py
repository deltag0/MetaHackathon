import csv
import os
import tempfile
from unittest.mock import patch


def _create_user(client, email="u@example.com", username="testuser"):
    return client.post("/users", json={"email": email, "username": username})


# GET /users

def test_get_users_list_empty(client):
    r = client.get("/users")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_get_users_list_returns_created(client):
    _create_user(client, "list@example.com", "listuser")
    r = client.get("/users")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) >= 1


def test_get_users_pagination(client):
    for i in range(15):
        _create_user(client, "page" + str(i) + "@example.com", "pageuser" + str(i))
    r = client.get("/users?page=1&per_page=10")
    assert r.status_code == 200
    assert len(r.get_json()) == 10


def test_get_users_pagination_page2(client):
    for i in range(15):
        _create_user(client, "pg2_" + str(i) + "@example.com", "pg2user" + str(i))
    r = client.get("/users?page=2&per_page=10")
    assert r.status_code == 200
    assert len(r.get_json()) == 5


# GET /users/<id>

def test_get_user_by_id(client):
    r = _create_user(client, "byid@example.com", "byiduser")
    user_id = r.get_json()["id"]
    r2 = client.get("/users/" + str(user_id))
    assert r2.status_code == 200
    assert r2.get_json()["id"] == user_id


def test_get_user_by_id_returns_fields(client):
    r = _create_user(client, "fields@example.com", "fieldsuser")
    uid = r.get_json()["id"]
    data = client.get("/users/" + str(uid)).get_json()
    assert data["email"] == "fields@example.com"
    assert data["username"] == "fieldsuser"


def test_get_nonexistent_user(client):
    r = client.get("/users/99999")
    assert r.status_code == 404
    assert "error" in r.get_json()


# POST /users

def test_create_user(client):
    r = client.post("/users", json={"email": "create@example.com", "username": "createuser"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["email"] == "create@example.com"
    assert data["username"] == "createuser"
    assert "id" in data


def test_create_user_missing_email(client):
    r = client.post("/users", json={"username": "noemail"})
    assert r.status_code == 400


def test_create_user_duplicate_email(client):
    client.post("/users", json={"email": "dup@example.com", "username": "dup1"})
    r = client.post("/users", json={"email": "dup@example.com", "username": "dup2"})
    assert r.status_code == 409


# PUT /users/<id>

def test_update_user(client):
    uid = _create_user(client, "upd@example.com", "oldname").get_json()["id"]
    r = client.put("/users/" + str(uid), json={"username": "newname"})
    assert r.status_code == 200
    assert r.get_json()["username"] == "newname"


def test_update_user_email(client):
    uid = _create_user(client, "oldemail@example.com", "emailuser").get_json()["id"]
    r = client.put("/users/" + str(uid), json={"email": "newemail@example.com"})
    assert r.status_code == 200
    assert r.get_json()["email"] == "newemail@example.com"


def test_update_nonexistent_user(client):
    r = client.put("/users/99999", json={"username": "ghost"})
    assert r.status_code == 404


# DELETE /users/<id>

def test_delete_user(client):
    uid = _create_user(client, "del@example.com", "deluser").get_json()["id"]
    r = client.delete("/users/" + str(uid))
    assert r.status_code == 200


def test_delete_user_removes_from_db(client):
    uid = _create_user(client, "gone@example.com", "goneuser").get_json()["id"]
    client.delete("/users/" + str(uid))
    assert client.get("/users/" + str(uid)).status_code == 404


def test_delete_nonexistent_user(client):
    r = client.delete("/users/99999")
    assert r.status_code == 404


# POST /users/bulk

def test_bulk_missing_file_returns_404(client):
    r = client.post("/users/bulk", json={"file": "nonexistent_file.csv"})
    assert r.status_code == 404


def test_bulk_load_users_success(client):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=["email", "username", "password_hash"])
        writer.writeheader()
        writer.writerow({"email": "bulkua@example.com", "username": "bulkua", "password_hash": ""})
        writer.writerow({"email": "bulkub@example.com", "username": "bulkub", "password_hash": ""})
        tmppath = f.name

    try:
        r = client.post("/users/bulk", json={"file": tmppath})
        assert r.status_code == 201
        assert r.get_json()["count"] == 2
    finally:
        os.unlink(tmppath)


# GET /users — additional branch coverage

def test_list_users_invalid_pagination_returns_400(client):
    r = client.get("/users?page=notanint")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_list_users_returns_cached_response(client):
    with patch("app.routes.users.cache_get", return_value=[{"id": 5, "email": "cached@example.com"}]):
        r = client.get("/users")
    assert r.status_code == 200
    assert r.get_json() == [{"id": 5, "email": "cached@example.com"}]


# GET /users/<id> — cache hit

def test_get_user_returns_cached_response(client):
    with patch("app.routes.users.cache_get", return_value={"id": 5, "email": "cached@example.com"}):
        r = client.get("/users/5")
    assert r.status_code == 200
    assert r.get_json()["id"] == 5


# POST /users — additional validation coverage

def test_create_user_email_not_string_returns_400(client):
    r = client.post("/users", json={"email": 12345})
    assert r.status_code == 400
    assert "string" in r.get_json()["error"]


# PUT /users/<id> — duplicate email

def test_update_user_to_existing_email_returns_409(client):
    client.post("/users", json={"email": "taken@example.com", "username": "u1"})
    uid2 = client.post("/users", json={"email": "other@example.com", "username": "u2"}).get_json()["id"]
    r = client.put("/users/" + str(uid2), json={"email": "taken@example.com"})
    assert r.status_code == 409
    assert "exists" in r.get_json()["error"]


def test_update_user_to_own_email_succeeds(client):
    uid = client.post("/users", json={"email": "own@example.com", "username": "ownuser"}).get_json()["id"]
    r = client.put("/users/" + str(uid), json={"email": "own@example.com"})
    assert r.status_code == 200
