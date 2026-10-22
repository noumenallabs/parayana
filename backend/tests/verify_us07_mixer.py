"""Verification suite for US-07:
Semicircle Spatial Mixer, C#3 Tanpura Bed, -14 LUFS Master & Synced Lyrics.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from config import PROJECTS_DIR, SAMPLE_RATE_MASTER
from db import (
    create_project,
    create_verses_batch,
    get_persona,
    get_project,
    init_db,
    update_verse,
)
from engine.mixer import assemble_project_master, mix_single_verse
from engine.stotra_parser import parse_stotra_or_sahasranama


def verify_us07() -> None:
    print("--- Verifying US-07: Semicircle Spatial Mixer & -14 LUFS Master Assembly ---")

    test_db_path = BACKEND_DIR / "storage" / "test_verify_us07.db"
    init_db(test_db_path)

    # 1. Setup test project and verses
    proj_id = f"test_proj_{uuid.uuid4().hex[:8]}"
    raw_stotra = (
        "पूर्वपीठिका\n"
        "शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।\n"
        "प्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥\n"
        "स्तोत्रम्\n"
        "विश्वं विष्णुर्वषट्कारो भूतभव्यभवत्प्रभुः ।\n"
        "भूतकृद्भूतभृद्भावो भूतात्मा भूतभावनः ॥"
    )

    parsed_units = parse_stotra_or_sahasranama(raw_stotra)
    assert len(parsed_units) == 2, f"Expected 2 parsed verses, got {len(parsed_units)}"

    proj_data = {
        "id": proj_id,
        "title": "Mastering Test Suite Project",
        "raw_input_text": raw_stotra,
        "render_mode": "studio_seedvc",
        "active_persona_ids_json": '["pandit_1_mukhya", "pandit_2_vriddha", "pandit_3_ghanapathi"]',
        "chant_speed": 0.90,
        "nfe_steps": 64,
        "cfg_strength": 3.0,
        "tanpura_gain_db": -18.0,
        "reverb_wet": 0.15,
        "inter_verse_pause_sec": 0.85,
        "section_pause_sec": 1.60,
        "choreography_mode": "AUTO_LITURGICAL",
        "status": "RENDERING",
    }
    create_project(proj_data, db_path=test_db_path)

    verse_records = []
    for u in parsed_units:
        v_idx = u["verse_index"]
        u["id"] = f"{proj_id}_{v_idx:03d}"
        u["project_id"] = proj_id
        verse_records.append(u)
    create_verses_batch(verse_records, db_path=test_db_path)

    # 2. Render test stems and mixed verses
    test_proj_dir = PROJECTS_DIR / proj_id
    test_proj_dir.mkdir(parents=True, exist_ok=True)
    takes_dir = test_proj_dir / "takes"
    takes_dir.mkdir(parents=True, exist_ok=True)

    # Prepare dummy pandit personas
    personas = [
        {"id": "pandit_1_mukhya", "default_pan": 0.0, "default_gain_db": 0.0},
        {"id": "pandit_2_vriddha", "default_pan": -0.22, "default_gain_db": -0.5},
        {"id": "pandit_3_ghanapathi", "default_pan": 0.22, "default_gain_db": -0.5},
    ]

    sr = SAMPLE_RATE_MASTER
    for v_idx in [1, 2]:
        dur_s = 6.0
        t = np.linspace(0, dur_s, int(dur_s * sr), endpoint=False)
        stem_paths = []
        for p_idx, p in enumerate(personas):
            # Synthesize stem with natural harmonic content
            f0 = 138.5913
            y_stem = (
                0.25 * np.sin(2 * np.pi * f0 * t)
                + 0.15 * np.sin(2 * np.pi * 2 * f0 * t)
                + 0.08 * np.sin(2 * np.pi * 3 * f0 * t)
            ) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.5 * t))
            stem_file = takes_dir / f"v{v_idx:03d}_{p['id']}.flac"
            sf.write(str(stem_file), y_stem.astype(np.float32), sr, format="FLAC", subtype="PCM_24")
            stem_paths.append(str(stem_file))

        mixed_verse_path = test_proj_dir / f"v{v_idx:03d}_mixed.wav"
        mix_single_verse(
            stem_paths=stem_paths,
            personas=personas,
            reverb_wet=0.15,
            out_wav=mixed_verse_path,
            choreography_mode="AUTO_LITURGICAL",
            unit_type="METRICAL_SLOKA",
            breath_windows=[[2.8, 3.2]],
            sr=sr,
        )

        update_verse(
            proj_id,
            v_idx,
            {
                "mixed_verse_wav_path": str(mixed_verse_path),
                "actual_duration_sec": dur_s,
                "qc_status": "PASS",
            },
            db_path=test_db_path,
        )

    # 3. Assemble Project Master
    master_result = assemble_project_master(
        project_id=proj_id,
        db_path=test_db_path,
    )

    master_wav_path = Path(master_result["master_wav_path"])
    srt_path = Path(master_result["srt_path"])
    lrc_path = Path(master_result["lrc_path"])

    # 4. Assert Output WAV properties: 48000 Hz, 2 channels, PCM_24
    assert master_wav_path.exists(), f"Master WAV missing: {master_wav_path}"
    wav_info = sf.info(str(master_wav_path))
    assert wav_info.samplerate == 48000, f"Expected 48000 Hz, got {wav_info.samplerate}"
    assert wav_info.channels == 2, f"Expected 2 channels (stereo), got {wav_info.channels}"
    assert wav_info.subtype == "PCM_24", f"Expected PCM_24, got {wav_info.subtype}"
    print(f"Master WAV verified: 48 kHz, 2 channels, PCM_24 ({wav_info.duration:.2f}s).")

    # 5. Assert integrated loudness within [-14.5, -13.5] LUFS and peak <= 0.892
    y_master, sr_m = sf.read(str(master_wav_path))
    meter = pyln.Meter(sr_m)
    lufs = meter.integrated_loudness(y_master)
    peak = float(np.max(np.abs(y_master)))

    print(f"Master Loudness: {lufs:.2f} LUFS (Target: -14.0 ± 0.5 LUFS)")
    print(f"Master Peak Amplitude: {peak:.4f} (Target: <= 0.892)")

    assert -14.5 <= lufs <= -13.5, f"Integrated loudness {lufs:.2f} LUFS outside [-14.5, -13.5] range"
    assert peak <= 0.892, f"Peak amplitude {peak:.4f} exceeds -1.0 dBTP limit (0.892)"

    # 6. Assert .srt and .lrc files contain timestamps for every verse
    assert srt_path.exists(), f"SRT file missing: {srt_path}"
    srt_text = srt_path.read_text(encoding="utf-8")
    assert "00:00:" in srt_text, "SRT missing valid timestamps"
    assert "शुक्लाम्बरधरं" in srt_text, "Verse 1 missing in SRT"
    assert "विश्वं विष्णुर्वषट्कारो" in srt_text, "Verse 2 missing in SRT"

    assert lrc_path.exists(), f"LRC file missing: {lrc_path}"
    lrc_text = lrc_path.read_text(encoding="utf-8")
    assert "[" in lrc_text and "]" in lrc_text, "LRC missing valid timestamps"
    assert "शुक्लाम्बरधरं" in lrc_text, "Verse 1 missing in LRC"
    assert "विश्वं विष्णुर्वषट्कारो" in lrc_text, "Verse 2 missing in LRC"

    print("SRT and LRC timing files verified.")

    # 7. Verify stems and split tracks ZIP archives
    stems_zip = Path(master_result["stems_zip_path"])
    split_zip = Path(master_result["split_tracks_zip_path"])
    assert stems_zip.exists(), "Stems ZIP archive missing"
    assert split_zip.exists(), "Spotify split tracks ZIP missing"
    print("Stems ZIP and Spotify split album tracks verified.")

    # Cleanup test project
    import shutil
    try:
        shutil.rmtree(test_proj_dir, ignore_errors=True)
        test_db_path.unlink(missing_ok=True)
        Path(str(test_db_path) + "-wal").unlink(missing_ok=True)
        Path(str(test_db_path) + "-shm").unlink(missing_ok=True)
    except Exception:
        pass

    print("VERIFY_PASS: US-07")


if __name__ == "__main__":
    verify_us07()
