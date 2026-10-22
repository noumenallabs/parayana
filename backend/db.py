"""Vāgdhenu Goṣṭhī Studio — SQLite Database & Persistence Layer.

Configures storage/studio.db with WAL mode, foreign key constraints,
thread-safe access, and full schema support for projects, verses (with 6 unit types
and liturgical choreography columns), and pandit personas.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from config import DB_PATH

_DB_LOCK = threading.RLock()


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Creates a thread-safe connection to SQLite with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        timeout=30.0,
        isolation_level=None,  # autocommit mode; we manage explicit transactions when needed
    )
    conn.row_factory = sqlite3.Row
    with _DB_LOCK:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    return conn


@contextmanager
def get_db(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing thread-safe database connection."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes tables and indexes in SQLite."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        with _DB_LOCK:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pandit_personas (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role_tag TEXT NOT NULL,
                    creation_mode TEXT NOT NULL,
                    recipe_json TEXT,
                    ref_wav_path TEXT NOT NULL,
                    cached_tensors_path TEXT NOT NULL,
                    default_pan REAL NOT NULL DEFAULT 0.0,
                    default_gain_db REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    raw_input_text TEXT NOT NULL,
                    render_mode TEXT NOT NULL DEFAULT 'preview_dsp',
                    active_persona_ids_json TEXT NOT NULL DEFAULT '[]',
                    chant_speed REAL NOT NULL DEFAULT 0.90,
                    nfe_steps INTEGER NOT NULL DEFAULT 64,
                    cfg_strength REAL NOT NULL DEFAULT 3.0,
                    tanpura_gain_db REAL NOT NULL DEFAULT -18.0,
                    reverb_wet REAL NOT NULL DEFAULT 0.15,
                    inter_verse_pause_sec REAL NOT NULL DEFAULT 0.85,
                    section_pause_sec REAL NOT NULL DEFAULT 1.60,
                    choreography_mode TEXT NOT NULL DEFAULT 'AUTO_LITURGICAL',
                    retain_intermediate_stems INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    master_wav_path TEXT,
                    lrc_path TEXT,
                    srt_path TEXT,
                    split_tracks_zip_path TEXT,
                    video_mp4_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS verses (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    verse_index INTEGER NOT NULL,
                    section_label TEXT NOT NULL DEFAULT 'स्तोत्रम्',
                    unit_type TEXT NOT NULL DEFAULT 'METRICAL_SLOKA',
                    choreography_override TEXT,
                    raw_text TEXT NOT NULL,
                    kannada_text TEXT NOT NULL,
                    slp1_text TEXT NOT NULL,
                    iast_text TEXT,
                    lg_signature TEXT,
                    syllable_count INTEGER NOT NULL DEFAULT 0,
                    detected_meter TEXT,
                    override_meter TEXT,
                    apply_internal_sandhi INTEGER NOT NULL DEFAULT 1,
                    base_seed INTEGER NOT NULL DEFAULT 100,
                    hemistich_split_sec REAL,
                    breath_windows_sec_json TEXT DEFAULT '[]',
                    expected_duration_sec REAL,
                    actual_duration_sec REAL,
                    qc_status TEXT NOT NULL DEFAULT 'PENDING',
                    qc_notes TEXT,
                    mixed_verse_wav_path TEXT,
                    UNIQUE(project_id, verse_index)
                );
                """
            )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_verses_proj_idx ON verses(project_id, verse_index);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_verses_qc_status ON verses(project_id, qc_status);")


# ── Project CRUD ─────────────────────────────────────────────────────────────

def create_project(project_data: Dict[str, Any], db_path: Path = DB_PATH) -> Dict[str, Any]:
    with get_db(db_path) as conn:
        with _DB_LOCK:
            cols = list(project_data.keys())
            placeholders = ", ".join([f":{c}" for c in cols])
            col_names = ", ".join(cols)
            sql = f"INSERT INTO projects ({col_names}) VALUES ({placeholders})"
            conn.execute(sql, project_data)
    return get_project(project_data["id"], db_path=db_path)  # type: ignore


def get_project(project_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_projects(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_project(project_id: str, updates: Dict[str, Any], db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    if not updates:
        return get_project(project_id, db_path=db_path)
    with get_db(db_path) as conn:
        with _DB_LOCK:
            set_clauses = [f"{k} = :{k}" for k in updates.keys()]
            sql = f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = :_id"
            payload = {**updates, "_id": project_id}
            conn.execute(sql, payload)
    return get_project(project_id, db_path=db_path)


def delete_project(project_id: str, db_path: Path = DB_PATH) -> bool:
    with get_db(db_path) as conn:
        with _DB_LOCK:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0


# ── Verse CRUD ───────────────────────────────────────────────────────────────

def create_verses_batch(verses: List[Dict[str, Any]], db_path: Path = DB_PATH) -> None:
    if not verses:
        return
    with get_db(db_path) as conn:
        with _DB_LOCK:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for v in verses:
                    cols = list(v.keys())
                    placeholders = ", ".join([f":{c}" for c in cols])
                    sql = f"INSERT OR REPLACE INTO verses ({', '.join(cols)}) VALUES ({placeholders})"
                    conn.execute(sql, v)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise


def get_verses_for_project(project_id: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM verses WHERE project_id = ? ORDER BY verse_index ASC",
            (project_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_verse(project_id: str, verse_index: int, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM verses WHERE project_id = ? AND verse_index = ?",
            (project_id, verse_index),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_verse(project_id: str, verse_index: int, updates: Dict[str, Any], db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    if not updates:
        return get_verse(project_id, verse_index, db_path=db_path)
    with get_db(db_path) as conn:
        with _DB_LOCK:
            set_clauses = [f"{k} = :{k}" for k in updates.keys()]
            sql = f"UPDATE verses SET {', '.join(set_clauses)} WHERE project_id = :_pid AND verse_index = :_vidx"
            payload = {**updates, "_pid": project_id, "_vidx": verse_index}
            conn.execute(sql, payload)
    return get_verse(project_id, verse_index, db_path=db_path)


# ── Persona CRUD ─────────────────────────────────────────────────────────────

def create_persona(persona_data: Dict[str, Any], db_path: Path = DB_PATH) -> Dict[str, Any]:
    with get_db(db_path) as conn:
        with _DB_LOCK:
            cols = list(persona_data.keys())
            placeholders = ", ".join([f":{c}" for c in cols])
            sql = f"INSERT OR REPLACE INTO pandit_personas ({', '.join(cols)}) VALUES ({placeholders})"
            conn.execute(sql, persona_data)
    return get_persona(persona_data["id"], db_path=db_path)  # type: ignore


def get_persona(persona_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM pandit_personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_personas(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM pandit_personas ORDER BY created_at ASC")
        return [dict(row) for row in cursor.fetchall()]


def delete_persona(persona_id: str, db_path: Path = DB_PATH) -> bool:
    with get_db(db_path) as conn:
        with _DB_LOCK:
            cursor = conn.execute("DELETE FROM pandit_personas WHERE id = ?", (persona_id,))
            return cursor.rowcount > 0
