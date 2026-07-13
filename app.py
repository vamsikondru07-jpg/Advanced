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




if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
