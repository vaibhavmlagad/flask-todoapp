import os
import tempfile
import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp()

import app as flask_app  # noqa: E402


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c
    # clean up rows between tests
    with flask_app.app.app_context():
        db = flask_app.get_db()
        db.execute("DELETE FROM todos")
        db.commit()


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_readyz(client):
    res = client.get("/readyz")
    assert res.status_code == 200


def test_create_todo_requires_title(client):
    res = client.post("/api/todos", json={"title": ""})
    assert res.status_code == 400


def test_create_and_list_todo(client):
    res = client.post("/api/todos", json={"title": "Buy milk", "priority": "high"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["title"] == "Buy milk"
    assert body["priority"] == "high"
    assert body["completed"] is False

    res = client.get("/api/todos")
    assert res.status_code == 200
    data = res.get_json()
    assert data["stats"]["total"] == 1
    assert data["stats"]["active"] == 1


def test_toggle_todo(client):
    created = client.post("/api/todos", json={"title": "Task"}).get_json()
    tid = created["id"]

    res = client.patch(f"/api/todos/{tid}/toggle")
    assert res.status_code == 200
    assert res.get_json()["completed"] is True

    res = client.patch(f"/api/todos/{tid}/toggle")
    assert res.get_json()["completed"] is False


def test_update_todo(client):
    created = client.post("/api/todos", json={"title": "Old title"}).get_json()
    tid = created["id"]

    res = client.put(f"/api/todos/{tid}", json={"title": "New title", "priority": "low"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["title"] == "New title"
    assert body["priority"] == "low"


def test_delete_todo(client):
    created = client.post("/api/todos", json={"title": "To delete"}).get_json()
    tid = created["id"]

    res = client.delete(f"/api/todos/{tid}")
    assert res.status_code == 200

    res = client.get(f"/api/todos/{tid}")
    assert res.status_code == 404


def test_clear_completed(client):
    a = client.post("/api/todos", json={"title": "A"}).get_json()
    client.post("/api/todos", json={"title": "B"})
    client.patch(f"/api/todos/{a['id']}/toggle")

    res = client.delete("/api/todos/clear-completed")
    assert res.status_code == 200

    data = client.get("/api/todos").get_json()
    assert data["stats"]["completed"] == 0
