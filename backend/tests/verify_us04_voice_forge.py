"""Verification suite for US-04:
Admin Pandit Persona Forge & 192-D Speaker Embedding Blender.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import torch

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from config import DB_PATH, PERSONAS_DIR, TONIC_CSHARP3_HZ
from db import get_persona, list_personas
from engine.voice_forge import blend_personas


def verify_us04() -> None:
    print("--- Verifying US-04: Admin Pandit Persona Forge & 192-D Embedding Blender ---")

    # 1. Assert all 5 default personas exist in SQLite
    expected_ids = [
        "pandit_1_mukhya",
        "pandit_2_vriddha",
        "pandit_3_ghanapathi",
        "pandit_4_yuva",
        "pandit_5_upagayaka",
    ]

    for p_id in expected_ids:
        row = get_persona(p_id, db_path=DB_PATH)
        assert row is not None, f"Persona '{p_id}' missing in SQLite database"
        assert Path(row["ref_wav_path"]).exists(), f"Reference WAV missing for '{p_id}': {row['ref_wav_path']}"
        assert Path(row["cached_tensors_path"]).exists(), f"Cached tensors missing for '{p_id}': {row['cached_tensors_path']}"
        print(f"Verified persona record & disk assets: {p_id}")

    # 2. Assert loaded style2 tensors have shape (1, 192)
    # 3. Assert F0_ori median voiced frequency falls within 138.59 ± 2.0 Hz (C#3) (C-04 Override)
    for p_id in expected_ids:
        row = get_persona(p_id, db_path=DB_PATH)
        cached_pt = Path(row["cached_tensors_path"])
        data = torch.load(str(cached_pt), map_location="cpu")

        assert "style2" in data, f"Key 'style2' missing in {cached_pt}"
        style2 = data["style2"]
        assert style2.shape == (1, 192), f"Expected style2 shape (1, 192), got {style2.shape}"

        assert "F0_ori" in data, f"Key 'F0_ori' missing in {cached_pt}"
        f0_ori = data["F0_ori"].numpy()
        voiced = f0_ori[f0_ori > 0]
        assert len(voiced) > 0, f"No voiced frames in F0_ori for {p_id}"
        med_f0 = float(np.median(voiced))
        diff = abs(med_f0 - TONIC_CSHARP3_HZ)
        assert diff <= 2.0, (
            f"Persona {p_id} F0_ori median {med_f0:.2f} Hz outside 138.59 ± 2.0 Hz (diff={diff:.2f} Hz)"
        )
        print(f"  {p_id}: style2 shape {tuple(style2.shape)}, median voiced F0 = {med_f0:.2f} Hz (C#3 anchor verified)")

    # 4. Assert blend_personas(..., alpha=0.5) produces valid vector with cosine sim in (0.40, 0.95) to both parents
    parent_a = PERSONAS_DIR / "pandit_1_mukhya_tensors.pt"
    parent_b = PERSONAS_DIR / "pandit_2_vriddha_tensors.pt"
    blended_out = PERSONAS_DIR / "test_blended_persona_tensors.pt"

    blend_res = blend_personas(
        persona_a_pt=parent_a,
        persona_b_pt=parent_b,
        alpha=0.5,
        out_pt_path=blended_out,
    )

    cos_a = blend_res["cosine_sim_a"]
    cos_b = blend_res["cosine_sim_b"]
    print(f"Blended Persona (alpha=0.5): cos_sim(Parent A) = {cos_a:.4f}, cos_sim(Parent B) = {cos_b:.4f}")

    assert 0.40 <= cos_a <= 0.95, f"Cosine similarity to Parent A {cos_a:.4f} not in (0.40, 0.95)"
    assert 0.40 <= cos_b <= 0.95, f"Cosine similarity to Parent B {cos_b:.4f} not in (0.40, 0.95)"

    # Verify blended file on disk
    blended_data = torch.load(str(blended_out), map_location="cpu")
    assert blended_data["style2"].shape == (1, 192), "Blended style2 tensor must have shape (1, 192)"

    # Clean up test blended file
    if blended_out.exists():
        blended_out.unlink()

    print("VERIFY_PASS: US-04")


if __name__ == "__main__":
    verify_us04()
