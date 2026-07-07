import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE = os.path.join(DATA_DIR, "todos.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT DEFAULT 'medium',
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.commit()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "priority": row["priority"],
        "completed": bool(row["completed"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/readyz")
def readyz():
    try:
        db = get_db()
        db.execute("SELECT 1")
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        return jsonify({"status": "not-ready", "error": str(e)}), 503


# ---------- REST API ----------

@app.route("/api/todos", methods=["GET"])
def get_todos():
    db = get_db()
    filter_status = request.args.get("status", "all")  # all, active, completed
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM todos WHERE 1=1"
    params = []

    if filter_status == "active":
        query += " AND completed = 0"
    elif filter_status == "completed":
        query += " AND completed = 1"

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY completed ASC, created_at DESC"
    rows = db.execute(query, params).fetchall()
    todos = [row_to_dict(r) for r in rows]

    total = len(db.execute("SELECT id FROM todos").fetchall())
    completed_count = len(db.execute("SELECT id FROM todos WHERE completed = 1").fetchall())

    return jsonify({
        "todos": todos,
        "stats": {
            "total": total,
            "completed": completed_count,
            "active": total - completed_count,
        }
    })


@app.route("/api/todos/<int:todo_id>", methods=["GET"])
def get_todo(todo_id):
    db = get_db()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Todo not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/api/todos", methods=["POST"])
def create_todo():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    priority = data.get("priority", "medium")

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if priority not in ("low", "medium", "high"):
        priority = "medium"

    now = datetime.utcnow().isoformat()
    db = get_db()
    cur = db.execute(
        "INSERT INTO todos (title, description, priority, completed, created_at, updated_at) "
        "VALUES (?, ?, ?, 0, ?, ?)",
        (title, description, priority, now, now),
    )
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    db = get_db()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Todo not found"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title", row["title"]).strip()
    description = data.get("description", row["description"])
    priority = data.get("priority", row["priority"])
    if priority not in ("low", "medium", "high"):
        priority = row["priority"]

    if not title:
        return jsonify({"error": "Title cannot be empty"}), 400

    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE todos SET title = ?, description = ?, priority = ?, updated_at = ? WHERE id = ?",
        (title, description, priority, now, todo_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/api/todos/<int:todo_id>/toggle", methods=["PATCH"])
def toggle_todo(todo_id):
    db = get_db()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Todo not found"}), 404

    new_status = 0 if row["completed"] else 1
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE todos SET completed = ?, updated_at = ? WHERE id = ?",
        (new_status, now, todo_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    db = get_db()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Todo not found"}), 404
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    return jsonify({"message": "Todo deleted", "id": todo_id})


@app.route("/api/todos/clear-completed", methods=["DELETE"])
def clear_completed():
    db = get_db()
    db.execute("DELETE FROM todos WHERE completed = 1")
    db.commit()
    return jsonify({"message": "Completed todos cleared"})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
