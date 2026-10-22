"""Verification suite for US-08:
FastAPI Control Plane, Real-Time SSE Render Queue & Video Exporter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from fastapi.testclient import TestClient

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from config import PROJECTS_DIR


def verify_us08() -> None:
    print("--- Verifying US-08: FastAPI Control Plane & Full Studio API Lifecycle ---")

    client = TestClient(app)

    # 1. GET /api/personas
    res_personas = client.get("/api/personas")
    assert res_personas.status_code == 200, f"GET /api/personas failed: {res_personas.text}"
    personas = res_personas.json()
    assert len(personas) >= 5, f"Expected at least 5 personas, found {len(personas)}"
    print(f"Verified {len(personas)} available pandit personas.")

    # 2. POST /api/projects
    sample_stotra = (
        "पूर्वपीठिका\n"
        "शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।\n"
        "प्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥\n"
        "स्तोत्रम्\n"
        "यस्य द्विरदवक्त्राद्याः पारिषद्याः परः शतम् ।\n"
        "विघ्नं निघ्नन्ति सततं विष्वक्सेनं तमाश्रये ॥"
    )
    proj_payload = {
        "title": "API Test Chanting Project",
        "raw_input_text": sample_stotra,
        "render_mode": "preview_dsp",
        "chant_speed": 0.90,
        "nfe_steps": 48,
        "cfg_strength": 3.0,
        "tanpura_gain_db": -18.0,
        "reverb_wet": 0.15,
        "inter_verse_pause_sec": 0.85,
        "section_pause_sec": 1.60,
        "choreography_mode": "AUTO_LITURGICAL",
        "retain_intermediate_stems": False,
    }
    res_proj = client.post("/api/projects", json=proj_payload)
    assert res_proj.status_code == 200, f"POST /api/projects failed: {res_proj.text}"
    proj = res_proj.json()
    proj_id = proj["id"]
    verses = proj["verses"]
    assert len(verses) == 2, f"Expected 2 parsed verses, got {len(verses)}"
    print(f"Created project {proj_id} with {len(verses)} verses.")

    # 3. GET /api/projects/{id}
    res_get = client.get(f"/api/projects/{proj_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == proj_id

    # 4. PATCH /api/projects/{id}/verses/{v_idx}
    patch_payload = {
        "override_meter": "anuṣṭubh",
        "choreography_override": "FULL_UNISON",
        "base_seed": 250,
    }
    res_patch = client.patch(f"/api/projects/{proj_id}/verses/1", json=patch_payload)
    assert res_patch.status_code == 200
    patched_v = res_patch.json()
    assert patched_v["override_meter"] == "anuṣṭubh"
    assert patched_v["base_seed"] == 250
    print("Patched verse 1 properties verified.")

    # 5. POST /api/projects/{id}/render
    # Execute render synchronously for test verification
    from main import _execute_project_render
    _execute_project_render(proj_id)

    res_post_render = client.get(f"/api/projects/{proj_id}")
    updated_proj = res_post_render.json()
    assert updated_proj["status"] == "COMPLETED"
    assert all(v["qc_status"] == "PASS" for v in updated_proj["verses"])
    print("Project render executed and all verses passed QC.")

    # 6. POST /api/projects/{id}/verses/{v_idx}/reroll
    res_reroll = client.post(f"/api/projects/{proj_id}/verses/1/reroll", json={"seed_offset": 101})
    assert res_reroll.status_code == 200
    rerolled = res_reroll.json()
    assert rerolled["base_seed"] == 351  # 250 + 101
    assert rerolled["qc_status"] == "PASS"
    print("Verse 1 seed re-roll verified.")

    # 7. POST /api/projects/{id}/master
    res_master = client.post(f"/api/projects/{proj_id}/master", json={})
    assert res_master.status_code == 200, f"Master export failed: {res_master.text}"
    master_info = res_master.json()
    assert "/audio/" in master_info["master_wav_url"]
    assert "/audio/" in master_info["srt_url"]
    assert "/audio/" in master_info["lrc_url"]
    assert -14.5 <= master_info["lufs"] <= -13.5
    print(f"Mastering verified: {master_info['lufs']:.2f} LUFS, Peak: {master_info['peak_dbtp']:.2f} dBTP.")

    # 8. POST /api/projects/{id}/export-video (C-03 Override)
    res_video = client.post(f"/api/projects/{proj_id}/export-video", json={"font_size": 38})
    assert res_video.status_code == 200, f"Video export failed: {res_video.text}"
    video_data = res_video.json()
    assert "video_mp4_url" in video_data
    print("Karaoke video export endpoint verified.")

    # 9. POST /api/personas/forge & POST /api/personas/blend
    forge_payload = {
        "name": "Śrī Śāstrī (Custom Forged)",
        "role_tag": "Lead Scholar",
        "prompt": "A dignified elder Sanskrit scholar chanting with gravitas",
        "formant_shift_st": -0.5,
        "chest_db": 2.0,
        "presence_db": 1.0,
        "air_db": 0.5,
        "default_pan": 0.15,
        "default_gain_db": 0.0,
    }
    res_forge = client.post("/api/personas/forge", json=forge_payload)
    assert res_forge.status_code == 200, f"Persona forge failed: {res_forge.text}"
    forged = res_forge.json()
    print(f"Admin Voice Forge created persona: {forged['id']}")

    blend_payload = {
        "name": "Śrī Saṅgama (Blended)",
        "role_tag": "Blended Scholar",
        "parent_a_id": "pandit_1_mukhya",
        "parent_b_id": "pandit_2_vriddha",
        "alpha": 0.5,
    }
    res_blend = client.post("/api/personas/blend", json=blend_payload)
    assert res_blend.status_code == 200, f"Persona blend failed: {res_blend.text}"
    blended = res_blend.json()
    print(f"Admin Voice Blender created persona: {blended['id']}")

    # 10. GET /audio/* with HTTP Range Request Support
    master_rel = master_info["master_wav_url"].replace("/audio/", "")
    res_audio_range = client.get(
        f"/audio/{master_rel}",
        headers={"Range": "bytes=0-1023"},
    )
    assert res_audio_range.status_code == 206, (
        f"Expected 206 Partial Content, got {res_audio_range.status_code}"
    )
    assert "bytes 0-1023/" in res_audio_range.headers.get("Content-Range", "")
    assert len(res_audio_range.content) == 1024
    print("HTTP Range header streaming (WaveSurfer.js support) verified.")

    # Cleanup project
    from db import delete_project
    delete_project(proj_id)
    import shutil
    shutil.rmtree(PROJECTS_DIR / proj_id, ignore_errors=True)

    print("VERIFY_PASS: US-08")


if __name__ == "__main__":
    verify_us08()
