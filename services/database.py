import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects.db")

def init_db():
    """Initialize the SQLite database and create the projects table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_phase TEXT,
            state_data JSON
        )
    ''')
    conn.commit()
    conn.close()

def save_project(name, current_phase, state_dict):
    """Save or update a project in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Serialize state_dict to JSON string
    state_json = json.dumps(state_dict)
    
    try:
        c.execute('''
            INSERT INTO projects (name, current_phase, state_data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                current_phase=excluded.current_phase,
                state_data=excluded.state_data,
                updated_at=CURRENT_TIMESTAMP
        ''', (name, current_phase, state_json))
        conn.commit()
    finally:
        conn.close()

def load_project(project_id):
    """Load a project's state by its ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "name": row["name"],
            "current_phase": row["current_phase"],
            "state_data": json.loads(row["state_data"])
        }
    return None

def list_projects():
    """List all saved projects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, name, updated_at, current_phase FROM projects ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_project(project_id):
    """Delete a project by its ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
