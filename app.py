from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "issues.db")

ALLOWED_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
ALLOWED_PRIORITIES = ["Low", "Medium", "High", "Critical"]


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us read columns by name, e.g. row["title"]
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Open',
            priority TEXT NOT NULL,
            reporter TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

def validate_issue_data(data, is_update=False):
    """Check incoming issue data and return a list of error messages.
    On create, title/reporter/priority are always required.
    On update, a field is only checked if it was actually sent."""
    errors = []

    if not is_update or "title" in data:
        if not str(data.get("title", "")).strip():
            errors.append("title is required and cannot be empty")

    if not is_update or "reporter" in data:
        if not str(data.get("reporter", "")).strip():
            errors.append("reporter is required and cannot be empty")

    if not is_update or "priority" in data:
        if data.get("priority") not in ALLOWED_PRIORITIES:
            errors.append(f"priority must be one of {ALLOWED_PRIORITIES}")

    if "status" in data and data.get("status") not in ALLOWED_STATUSES:
        errors.append(f"status must be one of {ALLOWED_STATUSES}")

    return errors

def issue_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "reporter": row["reporter"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "AIB Issue Tracker API"}), 200

@app.route("/api/issues", methods=["POST"])
def create_issue():
    data = request.get_json(silent=True) or {}

    errors = validate_issue_data(data, is_update=False)
    if errors:
        return jsonify({"errors": errors}), 400

    now = datetime.utcnow().isoformat()
    status = data.get("status", "Open")

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO issues (title, description, status, priority, reporter, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["title"].strip(),
            data.get("description", ""),
            status,
            data["priority"],
            data["reporter"].strip(),
            now,
            now,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid

    row = conn.execute("SELECT * FROM issues WHERE id = ?", (new_id,)).fetchone()
    conn.close()

    return jsonify(issue_to_dict(row)), 201

@app.route("/api/issues", methods=["GET"])
def list_issues():
    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")
    search_term = request.args.get("search")
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    # whitelist sort_by/order before using them in the query string,
    # since they can't be passed in as normal ? parameters
    if sort_by not in ("created_at", "priority", "status", "title"):
        sort_by = "created_at"
    if order not in ("asc", "desc"):
        order = "desc"

    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if priority_filter:
        query += " AND priority = ?"
        params.append(priority_filter)

    if search_term:
        query += " AND (title LIKE ? OR description LIKE ?)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term])

    query += f" ORDER BY {sort_by} {order.upper()}"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([issue_to_dict(row) for row in rows]), 200

    
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
