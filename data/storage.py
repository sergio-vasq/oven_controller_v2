import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import time

DB_PATH = Path(__file__).resolve().parent.parent / "parts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    temp_setpoint REAL NOT NULL,
    conveyor_speed REAL NOT NULL,
    notes TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""

class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def add_part(self, code: str, temp: float, speed: float, notes: str = "") -> int:
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "INSERT INTO parts (code, temp_setpoint, conveyor_speed, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (code, temp, speed, notes, now, now)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def update_part(self, code: str, temp: float, speed: float, notes: str = "") -> None:
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE parts SET temp_setpoint=?, conveyor_speed=?, notes=?, updated_at=? WHERE code=?",
                (temp, speed, notes, now, code)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_part(self, code: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM parts WHERE code=?", (code,))
            conn.commit()
        finally:
            conn.close()

    def get_part(self, code: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT * FROM parts WHERE code=?", (code,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def list_parts(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT * FROM parts ORDER BY code ASC")
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
