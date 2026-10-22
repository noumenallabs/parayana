"""Verification suite for US-02:
Resumable Project & Sahasranāma State Persistence.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import (
    init_db,
    get_connection,
    create_project,
    get_project,
    delete_project,
    create_verses_batch,
    get_verses_for_project,
    update_verse,
    create_persona,
    get_persona,
)
from schemas import UnitType, ChoreographyMode


def verify_us02() -> None:
    print("--- Verifying US-02: Resumable Project & Sahasranāma State Persistence ---")

    test_db_path = BACKEND_DIR / "storage" / "test_verify_us02.db"
    if test_db_path.exists():
        test_db_path.unlink()

    # 1. Initialize DB and Assert WAL Mode
    init_db(test_db_path)
    conn = get_connection(test_db_path)
    mode_row = conn.execute("PRAGMA journal_mode;").fetchone()
    conn.close()
    assert mode_row is not None, "Failed to query journal_mode"
    journal_mode = mode_row[0].lower()
    print(f"Database journal mode: {journal_mode}")
    assert journal_mode == "wal", f"Expected 'wal' journal mode, got '{journal_mode}'"

    # 2. Insert 1 Project with 108 Verse Records
    proj_id = str(uuid.uuid4())
    proj_data = {
        "id": proj_id,
        "title": "Śrī Viṣṇu Sahasranāma Stotram (108 Test Verses)",
        "raw_input_text": "ॐ नमो भगवते वासुदेवाय...",
        "render_mode": "studio_seedvc",
        "active_persona_ids_json": '["pandit_1", "pandit_2", "pandit_3", "pandit_4", "pandit_5"]',
        "chant_speed": 0.90,
        "nfe_steps": 64,
        "cfg_strength": 3.0,
        "tanpura_gain_db": -18.0,
        "reverb_wet": 0.15,
        "inter_verse_pause_sec": 0.85,
        "section_pause_sec": 1.60,
        "choreography_mode": ChoreographyMode.AUTO_LITURGICAL.value,
        "retain_intermediate_stems": 0,
        "status": "PENDING",
    }
    created_proj = create_project(proj_data, db_path=test_db_path)
    assert created_proj is not None, "Failed to create project"
    assert created_proj["id"] == proj_id

    # Create 108 verses across diverse unit types
    unit_types = [
        UnitType.UVACA_CONNECTIVE.value,
        UnitType.METRICAL_SLOKA.value,
        UnitType.NAMAVALI_108.value,
        UnitType.GADYA_PROSE.value,
        UnitType.JAPA_REPEAT.value,
        UnitType.REFRAIN_HOOK.value,
    ]

    verses = []
    for i in range(1, 109):
        ut = unit_types[i % len(unit_types)]
        verses.append({
            "id": f"{proj_id}_{i:03d}",
            "project_id": proj_id,
            "verse_index": i,
            "section_label": "स्तोत्रम्" if i > 5 else "पूर्वपीठिका",
            "unit_type": ut,
            "choreography_override": None,
            "raw_text": f"Verse text line {i} sample śloka",
            "kannada_text": f"ವರ್ಸ್ ಟೆಕ್ಸ್ಟ್ ಲೈನ್ {i}",
            "slp1_text": f"verse text lEna {i}",
            "iast_text": f"verse text line {i}",
            "lg_signature": "LG" * 8,
            "syllable_count": 32,
            "detected_meter": "anuṣṭubh",
            "override_meter": None,
            "apply_internal_sandhi": 1,
            "base_seed": 100 + i * 37,
            "hemistich_split_sec": 4.5,
            "breath_windows_sec_json": "[[4.3, 4.7]]",
            "expected_duration_sec": 9.2,
            "actual_duration_sec": None,
            "qc_status": "PENDING",
            "qc_notes": None,
            "mixed_verse_wav_path": None,
        })

    create_verses_batch(verses, db_path=test_db_path)
    fetched_verses = get_verses_for_project(proj_id, db_path=test_db_path)
    assert len(fetched_verses) == 108, f"Expected 108 verses, found {len(fetched_verses)}"
    print(f"Successfully inserted and verified {len(fetched_verses)} verse records.")

    # 3. Concurrent Read/Write Updates from Multiple Threads
    errors = []

    def worker_writer():
        try:
            for v_idx in range(1, 55):
                update_verse(
                    proj_id,
                    v_idx,
                    {
                        "qc_status": "PASS",
                        "actual_duration_sec": 9.15,
                        "qc_notes": "Clean harmonic ratio",
                    },
                    db_path=test_db_path,
                )
                time.sleep(0.002)
        except Exception as e:
            errors.append(f"Writer error: {e}")

    def worker_reader_updater():
        try:
            for v_idx in range(55, 109):
                update_verse(
                    proj_id,
                    v_idx,
                    {
                        "qc_status": "PASS",
                        "actual_duration_sec": 9.22,
                        "qc_notes": "Valid timing gate",
                    },
                    db_path=test_db_path,
                )
                _ = get_verses_for_project(proj_id, db_path=test_db_path)
                time.sleep(0.002)
        except Exception as e:
            errors.append(f"Reader error: {e}")

    t1 = threading.Thread(target=worker_writer)
    t2 = threading.Thread(target=worker_reader_updater)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Concurrent thread operations failed with errors: {errors}"
    all_updated = get_verses_for_project(proj_id, db_path=test_db_path)
    assert all(v["qc_status"] == "PASS" for v in all_updated), "All 108 verses should be updated to PASS"
    print("Concurrent read/write updates verified without SQLite contention.")

    # 4. Verify Foreign-Key Cascade Deletion
    deleted = delete_project(proj_id, db_path=test_db_path)
    assert deleted, "Failed to delete project"
    orphaned_verses = get_verses_for_project(proj_id, db_path=test_db_path)
    assert len(orphaned_verses) == 0, f"Expected 0 orphaned verses, found {len(orphaned_verses)}"
    print("Foreign-key cascade deletion verified.")

    # Cleanup test db
    try:
        test_db_path.unlink(missing_ok=True)
        wal_path = Path(str(test_db_path) + "-wal")
        shm_path = Path(str(test_db_path) + "-shm")
        wal_path.unlink(missing_ok=True)
        shm_path.unlink(missing_ok=True)
    except Exception:
        pass

    print("VERIFY_PASS: US-02")


if __name__ == "__main__":
    verify_us02()
