"""Verification suite for US-05:
Persistent Vāgdhenu + BigVGAN-v2 Synthesis & Self-Healing Quality Control.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from engine.chant_worker import ChantWorker
from engine.stotra_parser import parse_stotra_or_sahasranama
from schemas import QCStatus


def verify_us05() -> None:
    print("--- Verifying US-05: Persistent Vāgdhenu Synthesis & Self-Healing QC ---")

    # 1. Parse sample verse: वसुदेवसुतं देवं...
    verse_text = (
        "वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।\n"
        "देवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥"
    )
    units = parse_stotra_or_sahasranama(verse_text)
    assert len(units) == 1, "Failed to parse test verse"
    verse = units[0]
    verse["project_id"] = "test_us05_project"

    test_out_dir = BACKEND_DIR / "storage" / "test_us05_takes"
    test_out_dir.mkdir(parents=True, exist_ok=True)

    # 2. Synthesize with num_takes=2
    worker = ChantWorker()
    synth_res = worker.synthesize_verse_takes(
        verse=verse,
        num_takes=2,
        nfe=64,
        cfg=3.0,
        speed=0.90,
        out_dir=test_out_dir,
    )

    take_paths = synth_res["take_paths"]
    assert len(take_paths) == 2, f"Expected 2 takes, got {len(take_paths)}"
    print(f"Generated 2 takes: {take_paths[0]}, {take_paths[1]}")

    # 3. Assert both 24 kHz WAVs exist and pass QC
    assert synth_res["qc_status"] == QCStatus.PASS.value, (
        f"QC failed with status {synth_res['qc_status']}: {synth_res['qc_notes']}"
    )

    take1_path = Path(take_paths[0])
    take2_path = Path(take_paths[1])
    assert take1_path.exists(), f"Missing take 1 file: {take1_path}"
    assert take2_path.exists(), f"Missing take 2 file: {take2_path}"

    y1, sr1 = sf.read(str(take1_path))
    y2, sr2 = sf.read(str(take2_path))

    assert sr1 == 24000, f"Expected 24000 Hz for take 1, got {sr1}"
    assert sr2 == 24000, f"Expected 24000 Hz for take 2, got {sr2}"

    dur1 = len(y1) / sr1
    dur2 = len(y2) / sr2
    print(f"Take 1 duration: {dur1:.2f}s, Take 2 duration: {dur2:.2f}s")

    # 4. Assert duration in [7.0s, 13.0s]
    assert 7.0 <= dur1 <= 13.0, f"Take 1 duration {dur1:.2f}s not in [7.0s, 13.0s]"
    assert 7.0 <= dur2 <= 13.0, f"Take 2 duration {dur2:.2f}s not in [7.0s, 13.0s]"

    # 5. Assert envelope correlation between 0.80 and 0.999
    win = int(0.025 * sr1)  # 25ms window
    min_len = min(len(y1), len(y2))
    env1 = [float(np.sqrt(np.mean(y1[i : i + win] ** 2))) for i in range(0, min_len - win, win)]
    env2 = [float(np.sqrt(np.mean(y2[i : i + win] ** 2))) for i in range(0, min_len - win, win)]

    corr = float(np.corrcoef(env1, env2)[0, 1])
    print(f"Takes envelope correlation: {corr:.4f}")

    assert 0.80 <= corr <= 0.999, (
        f"Envelope correlation {corr:.4f} outside expected range [0.80, 0.999]"
    )

    # 6. Verify breath coordinates detected
    breath_coords = synth_res["breath_windows_sec_json"]
    assert breath_coords and breath_coords != "[]", "Breath coordinates should be detected for 2-hemistich verse"
    print(f"Detected daṇḍa breath windows: {breath_coords}")

    # Cleanup test takes
    try:
        take1_path.unlink(missing_ok=True)
        take2_path.unlink(missing_ok=True)
        test_out_dir.rmdir()
    except Exception:
        pass

    print("VERIFY_PASS: US-05")


if __name__ == "__main__":
    verify_us05()
