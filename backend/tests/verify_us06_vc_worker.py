"""Verification suite for US-06:
Dual-Mode Ensemble Converter (Fast DSP Preview & F0-Locked Seed-VC Master).
"""

from __future__ import annotations

import sys
from pathlib import Path
import librosa
import numpy as np
import soundfile as sf
from scipy.spatial.distance import cosine

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from config import DB_PATH, TONIC_CSHARP3_HZ
from db import get_persona
from engine.chant_worker import ChantWorker
from engine.stotra_parser import parse_stotra_or_sahasranama
from engine.vc_worker import VCWorker


def verify_us06() -> None:
    print("--- Verifying US-06: Dual-Mode Ensemble Converter (Preview & Master) ---")

    # 1. Fetch default test personas: pandit_1_mukhya and pandit_2_vriddha
    p1 = get_persona("pandit_1_mukhya", DB_PATH)
    p2 = get_persona("pandit_2_vriddha", DB_PATH)
    assert p1 is not None and p2 is not None, "Failed to load default personas from DB"

    # 2. Synthesize base master take for sample verse
    verse_text = (
        "वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।\n"
        "देवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥"
    )
    units = parse_stotra_or_sahasranama(verse_text)
    verse = units[0]
    verse["project_id"] = "test_us06_proj"

    test_dir = BACKEND_DIR / "storage" / "test_us06_stems"
    test_dir.mkdir(parents=True, exist_ok=True)

    chant_worker = ChantWorker()
    take_res = chant_worker.synthesize_verse_takes(
        verse=verse,
        num_takes=1,
        out_dir=test_dir,
    )
    master_take = take_res["master_take_path"]
    assert master_take and Path(master_take).exists(), "Master take synthesis failed"

    vc_worker = VCWorker()

    # 3. Test Mode A: Fast DSP Preview
    preview_dir = test_dir / "preview"
    preview_stems = vc_worker.render_preview_dsp_stems(
        base_take_wav=master_take,
        personas=[p1, p2],
        out_dir=preview_dir,
        verse_idx=1,
    )
    assert len(preview_stems) == 2, f"Expected 2 preview stems, got {len(preview_stems)}"
    for st in preview_stems:
        assert Path(st).exists(), f"Preview stem missing: {st}"
        info = sf.info(st)
        assert info.format == "FLAC", f"Expected FLAC format, got {info.format}"
        assert info.subtype == "PCM_24", f"Expected 24-bit FLAC, got {info.subtype}"
    print(f"Fast DSP Preview verified: 2 x 24-bit FLAC stems generated.")

    # 4. Test Mode B: Studio Master Seed-VC
    studio_dir = test_dir / "studio"
    studio_stems = vc_worker.render_studio_seedvc_stems(
        take_wavs=master_take,
        personas=[p1, p2],
        out_dir=studio_dir,
        verse_idx=1,
        hemistich_split_sec=verse.get("hemistich_split_sec"),
    )
    assert len(studio_stems) == 2, f"Expected 2 studio stems, got {len(studio_stems)}"
    for st in studio_stems:
        assert Path(st).exists(), f"Studio stem missing: {st}"
        info = sf.info(st)
        assert info.format == "FLAC", f"Expected FLAC format, got {info.format}"
        assert info.subtype == "PCM_24", f"Expected 24-bit FLAC, got {info.subtype}"
    print(f"Studio Master Seed-VC verified: 2 x 24-bit FLAC stems generated.")

    # 5. Assert median voiced F0 of both studio_seedvc stems matches within 2.5 Hz (Unison Lock)
    y1, sr1 = sf.read(studio_stems[0])
    y2, sr2 = sf.read(studio_stems[1])

    f0_1, v1, _ = librosa.pyin(y1.astype(np.float32), fmin=65.0, fmax=350.0, sr=sr1)
    f0_2, v2, _ = librosa.pyin(y2.astype(np.float32), fmin=65.0, fmax=350.0, sr=sr2)

    voiced1 = f0_1[v1 & ~np.isnan(f0_1)]
    voiced2 = f0_2[v2 & ~np.isnan(f0_2)]
    assert len(voiced1) > 0 and len(voiced2) > 0, "No voiced frames detected in stems"

    med1 = float(np.median(voiced1))
    med2 = float(np.median(voiced2))
    f0_diff = abs(med1 - med2)
    print(f"Stem 1 median F0: {med1:.2f} Hz | Stem 2 median F0: {med2:.2f} Hz | Diff: {f0_diff:.2f} Hz")
    assert f0_diff <= 2.5, f"Unison pitch diff {f0_diff:.2f} Hz exceeds 2.5 Hz limit"

    # 6. Assert MFCC delta cosine distance exceeds 0.05 (Distinct Timbral Envelopes)
    m1 = librosa.feature.mfcc(y=y1.astype(np.float32), sr=sr1, n_mfcc=20)
    m2 = librosa.feature.mfcc(y=y2.astype(np.float32), sr=sr2, n_mfcc=20)
    d1 = librosa.feature.delta(m1).flatten()
    d2 = librosa.feature.delta(m2).flatten()

    mfcc_dist = float(cosine(d1, d2))
    print(f"Stems MFCC delta cosine distance: {mfcc_dist:.4f}")
    assert mfcc_dist > 0.05, f"MFCC distance {mfcc_dist:.4f} must exceed 0.05 for distinct timbres"

    # Cleanup test stems
    import shutil
    try:
        shutil.rmtree(test_dir, ignore_errors=True)
    except Exception:
        pass

    print("VERIFY_PASS: US-06")


if __name__ == "__main__":
    verify_us06()
