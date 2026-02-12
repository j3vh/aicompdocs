"""Database operations for storing algorithm snapshots and detected changes."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "algorithms.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at TEXT NOT NULL,
            total_algorithms INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS algorithms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            lars TEXT NOT NULL,
            name TEXT,
            organization TEXT,
            status TEXT,
            category TEXT,
            description_short TEXT,
            data_json TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_algorithms_lars
            ON algorithms(lars);
        CREATE INDEX IF NOT EXISTS idx_algorithms_snapshot
            ON algorithms(snapshot_id);

        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            lars TEXT NOT NULL,
            name TEXT,
            organization TEXT,
            change_type TEXT NOT NULL,
            changed_fields TEXT,
            old_values TEXT,
            new_values TEXT,
            detected_at TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_changes_snapshot
            ON changes(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_changes_lars
            ON changes(lars);
        CREATE INDEX IF NOT EXISTS idx_changes_type
            ON changes(change_type);
    """)
    conn.commit()


def create_snapshot(conn: sqlite3.Connection, total: int) -> int:
    cursor = conn.execute(
        "INSERT INTO snapshots (fetched_at, total_algorithms) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), total),
    )
    conn.commit()
    return cursor.lastrowid


def store_algorithm(
    conn: sqlite3.Connection, snapshot_id: int, lars: str, data: dict
) -> None:
    conn.execute(
        """INSERT INTO algorithms
           (snapshot_id, lars, name, organization, status, category, description_short, data_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot_id,
            lars,
            data.get("name", ""),
            data.get("organization", data.get("organisation", "")),
            data.get("status", ""),
            data.get("publication_category", data.get("category", "")),
            data.get("description_short", ""),
            json.dumps(data, ensure_ascii=False, default=str),
        ),
    )


def store_change(
    conn: sqlite3.Connection,
    snapshot_id: int,
    lars: str,
    name: str,
    organization: str,
    change_type: str,
    changed_fields: list[str] | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    conn.execute(
        """INSERT INTO changes
           (snapshot_id, lars, name, organization, change_type,
            changed_fields, old_values, new_values, detected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot_id,
            lars,
            name,
            organization,
            change_type,
            json.dumps(changed_fields, ensure_ascii=False) if changed_fields else None,
            json.dumps(old_values, ensure_ascii=False, default=str) if old_values else None,
            json.dumps(new_values, ensure_ascii=False, default=str) if new_values else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def get_latest_snapshot_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT id FROM snapshots ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["id"] if row else None


def get_previous_snapshot_id(conn: sqlite3.Connection, current_id: int) -> int | None:
    row = conn.execute(
        "SELECT id FROM snapshots WHERE id < ? ORDER BY id DESC LIMIT 1",
        (current_id,),
    ).fetchone()
    return row["id"] if row else None


def get_algorithms_for_snapshot(
    conn: sqlite3.Connection, snapshot_id: int
) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT lars, data_json FROM algorithms WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchall()
    return {row["lars"]: json.loads(row["data_json"]) for row in rows}


def get_all_changes(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT c.*, s.fetched_at
           FROM changes c
           JOIN snapshots s ON c.snapshot_id = s.id
           ORDER BY c.detected_at DESC"""
    ).fetchall()
    return [dict(row) for row in rows]


def get_changes_for_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM changes WHERE snapshot_id = ? ORDER BY change_type, name",
        (snapshot_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_all_snapshots(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM snapshots ORDER BY id DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_changes_for_lars(conn: sqlite3.Connection, lars: str) -> list[dict]:
    rows = conn.execute(
        """SELECT c.*, s.fetched_at
           FROM changes c
           JOIN snapshots s ON c.snapshot_id = s.id
           WHERE c.lars = ?
           ORDER BY c.detected_at DESC""",
        (lars,),
    ).fetchall()
    return [dict(row) for row in rows]
