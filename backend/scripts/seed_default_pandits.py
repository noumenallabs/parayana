"""Vāgdhenu Goṣṭhī Studio — Seed Default 5-Pandit Ensemble Personas.

Provisions the five canonical virtual pandits:
  1. pandit_1_mukhya: Lead Center, 0.0 st, pan 0.0, gain 0.0 dB
  2. pandit_2_vriddha: Deep Elder, -1.4 st, pan -0.22, gain -0.5 dB
  3. pandit_3_ghanapathi: Bass-Baritone, -0.8 st, pan +0.22, gain -0.5 dB
  4. pandit_4_yuva: Bright Tenor, +1.1 st, pan -0.45, gain -1.0 dB
  5. pandit_5_upagayaka: Warm Support, +0.5 st, pan +0.45, gain -1.0 dB

Anchors all reference WAVs and cached tensors to 138.59 Hz (C#3) (F-02, Flaw 14).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from config import DB_PATH, PERSONAS_DIR
from db import create_persona, init_db
from voice_forge import (
    extract_and_cache_seedvc_tensors,
    sculpt_vocal_tract,
    synthesize_calibration_reference,
)

DEFAULT_PANDITS = [
    {
        "id": "pandit_1_mukhya",
        "name": "Śrī Mukhya Pandit (Lead Center)",
        "role_tag": "Lead Center",
        "timbre": "baritone",
        "formant_shift_st": 0.0,
        "default_pan": 0.0,
        "default_gain_db": 0.0,
        "chest_db": 1.0,
        "presence_db": 1.5,
        "air_db": 0.5,
    },
    {
        "id": "pandit_2_vriddha",
        "name": "Śrī Vṛddha Pandit (Deep Elder)",
        "role_tag": "Deep Elder",
        "timbre": "elder",
        "formant_shift_st": -1.4,
        "default_pan": -0.22,
        "default_gain_db": -0.5,
        "chest_db": 3.5,
        "presence_db": -1.0,
        "air_db": -1.5,
    },
    {
        "id": "pandit_3_ghanapathi",
        "name": "Śrī Ghanapāṭhī (Bass-Baritone)",
        "role_tag": "Bass-Baritone",
        "timbre": "bass",
        "formant_shift_st": -0.8,
        "default_pan": 0.22,
        "default_gain_db": -0.5,
        "chest_db": 2.5,
        "presence_db": 2.0,
        "air_db": 0.0,
    },
    {
        "id": "pandit_4_yuva",
        "name": "Śrī Yuva Pandit (Bright Tenor)",
        "role_tag": "Bright Tenor",
        "timbre": "tenor",
        "formant_shift_st": 1.1,
        "default_pan": -0.45,
        "default_gain_db": -1.0,
        "chest_db": -1.5,
        "presence_db": 1.5,
        "air_db": 2.5,
    },
    {
        "id": "pandit_5_upagayaka",
        "name": "Śrī Upagāyaka (Warm Support)",
        "role_tag": "Warm Support",
        "timbre": "baritone",
        "formant_shift_st": 0.5,
        "default_pan": 0.45,
        "default_gain_db": -1.0,
        "chest_db": 0.5,
        "presence_db": 0.5,
        "air_db": 1.0,
    },
]


def seed_pandits(db_path: Path = DB_PATH) -> None:
    init_db(db_path)
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Seeding Default 5-Pandit Ensemble Personas ===")

    for idx, p in enumerate(DEFAULT_PANDITS):
        p_id = p["id"]
        raw_ref_wav = PERSONAS_DIR / f"{p_id}_raw.wav"
        sculpted_wav = PERSONAS_DIR / f"{p_id}_ref.wav"
        tensors_pt = PERSONAS_DIR / f"{p_id}_tensors.pt"

        print(f"[{idx+1}/5] Provisioning {p['name']} ({p_id})...")

        # 1. Synthesize reference calibration audio with sustained vowels (Flaw 14)
        synthesize_calibration_reference(
            raw_ref_wav,
            duration_sec=12.0,
            vocal_timbre=p["timbre"],
        )

        # 2. Sculpt vocal tract and apply 3-band EQ
        sculpt_vocal_tract(
            in_wav=raw_ref_wav,
            out_wav=sculpted_wav,
            formant_shift_st=p["formant_shift_st"],
            chest_db=p["chest_db"],
            presence_db=p["presence_db"],
            air_db=p["air_db"],
        )

        # 3. Extract and cache tensors (F0 pre-normalized to 138.59 Hz C#3)
        extract_and_cache_seedvc_tensors(
            ref_wav_path=sculpted_wav,
            out_pt_path=tensors_pt,
            seed=100 + idx * 79,
        )

        # Clean up temporary raw WAV
        if raw_ref_wav.exists():
            raw_ref_wav.unlink()

        # 4. Save to database
        recipe = {
            "formant_shift_st": p["formant_shift_st"],
            "chest_db": p["chest_db"],
            "presence_db": p["presence_db"],
            "air_db": p["air_db"],
            "timbre": p["timbre"],
        }
        persona_record = {
            "id": p_id,
            "name": p["name"],
            "role_tag": p["role_tag"],
            "creation_mode": "PRESET_FORGED",
            "recipe_json": json.dumps(recipe),
            "ref_wav_path": str(sculpted_wav),
            "cached_tensors_path": str(tensors_pt),
            "default_pan": p["default_pan"],
            "default_gain_db": p["default_gain_db"],
        }
        create_persona(persona_record, db_path=db_path)
        print(f"    Saved {p_id} to database. Pan: {p['default_pan']}, Gain: {p['default_gain_db']} dB")

    print("All 5 default pandits successfully seeded!")


if __name__ == "__main__":
    seed_pandits()
