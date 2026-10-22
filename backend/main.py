"""Vāgdhenu Goṣṭhī Studio — FastAPI Control Plane & SSE Real-Time Render Queue.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from config import (
    DB_PATH,
    PERSONAS_DIR,
    PROJECTS_DIR,
    STORAGE_DIR,
)
from db import (
    create_persona,
    create_project,
    create_verses_batch,
    get_persona,
    get_project,
    get_verse,
    get_verses_for_project,
    init_db,
    list_personas,
    list_projects,
    update_project,
    update_verse,
)
from engine.chant_worker import ChantWorker
from engine.mixer import assemble_project_master, mix_single_verse
from engine.stotra_parser import parse_stotra_or_sahasranama
from engine.vc_worker import VCWorker
from engine.video_exporter import export_karaoke_video
from engine.voice_forge import (
    blend_personas,
    extract_and_cache_seedvc_tensors,
    generate_parler_reference,
    sculpt_vocal_tract,
)
from schemas import (
    MasterExportRequest,
    MasterExportResponse,
    PersonaBlendRequest,
    PersonaCreateRequest,
    PersonaResponse,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectStatus,
    RerollVerseRequest,
    VerseResponse,
    VerseUpdateRequest,
    VideoExportRequest,
)

# Initialize database schema at startup
init_db(DB_PATH)

app = FastAPI(
    title="Vāgdhenu Goṣṭhī Studio API",
    version="2.1.0",
    description="Multi-Pandit Sanskrit Chanting Engine & Neural Vocal Ensemble Studio",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global event subscribers for SSE: project_id -> list of asyncio.Queue
_SSE_SUBSCRIBERS: Dict[str, List[asyncio.Queue]] = {}


def broadcast_event(project_id: str, event_data: Dict[str, Any]) -> None:
    """Broadcasts real-time events to all SSE clients connected to project_id."""
    queues = _SSE_SUBSCRIBERS.get(project_id, [])
    payload = json.dumps(event_data)
    for q in queues:
        try:
            q.put_nowait(payload)
        except Exception:
            pass


# ── Projects Endpoints ───────────────────────────────────────────────────────

@app.post("/api/projects", response_model=ProjectDetailResponse)
def api_create_project(req: ProjectCreateRequest) -> Any:
    proj_id = f"proj_{uuid.uuid4().hex[:10]}"

    # Parse input text into structured verses
    parsed_units = parse_stotra_or_sahasranama(
        raw_text=req.raw_input_text,
        japa_repeat_count=req.japa_repeat_count,
        apply_sandhi=True,
    )
    if not parsed_units:
        raise HTTPException(status_code=400, detail="Failed to parse any verses from input text.")

    # Insert project record
    proj_data = {
        "id": proj_id,
        "title": req.title,
        "raw_input_text": req.raw_input_text,
        "render_mode": req.render_mode.value,
        "active_persona_ids_json": json.dumps(req.active_persona_ids or ["pandit_1_mukhya", "pandit_2_vriddha", "pandit_3_ghanapathi", "pandit_4_yuva", "pandit_5_upagayaka"]),
        "chant_speed": req.chant_speed,
        "nfe_steps": req.nfe_steps,
        "cfg_strength": req.cfg_strength,
        "tanpura_gain_db": req.tanpura_gain_db,
        "reverb_wet": req.reverb_wet,
        "inter_verse_pause_sec": req.inter_verse_pause_sec,
        "section_pause_sec": req.section_pause_sec,
        "choreography_mode": req.choreography_mode.value,
        "retain_intermediate_stems": int(req.retain_intermediate_stems),
        "status": ProjectStatus.PENDING.value,
    }
    create_project(proj_data, db_path=DB_PATH)

    # Insert verses
    verse_records = []
    for u in parsed_units:
        v_idx = u["verse_index"]
        u["id"] = f"{proj_id}_{v_idx:03d}"
        u["project_id"] = proj_id
        verse_records.append(u)
    create_verses_batch(verse_records, db_path=DB_PATH)

    return api_get_project(proj_id)


@app.get("/api/projects", response_model=List[Dict[str, Any]])
def api_list_projects() -> Any:
    return list_projects(db_path=DB_PATH)


@app.get("/api/projects/{project_id}", response_model=ProjectDetailResponse)
def api_get_project(project_id: str) -> Any:
    p = get_project(project_id, db_path=DB_PATH)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    verses = get_verses_for_project(project_id, db_path=DB_PATH)

    # Decode JSON fields
    active_ids = json.loads(p.get("active_persona_ids_json") or "[]")
    p["active_persona_ids"] = active_ids
    p["verses"] = verses
    return p


@app.patch("/api/projects/{project_id}/verses/{verse_index}", response_model=VerseResponse)
def api_update_verse(project_id: str, verse_index: int, req: VerseUpdateRequest) -> Any:
    updates = {}
    if req.override_meter is not None:
        updates["override_meter"] = req.override_meter
    if req.choreography_override is not None:
        updates["choreography_override"] = req.choreography_override
    if req.apply_internal_sandhi is not None:
        updates["apply_internal_sandhi"] = int(req.apply_internal_sandhi)
    if req.base_seed is not None:
        updates["base_seed"] = req.base_seed

    updated = update_verse(project_id, verse_index, updates, db_path=DB_PATH)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Verse {verse_index} not found for project {project_id}")
    return updated


# ── Render Engine Execution ──────────────────────────────────────────────────

def _execute_project_render(project_id: str) -> None:
    """Renders all verses sequentially and broadcasts SSE progress events."""
    proj = get_project(project_id, db_path=DB_PATH)
    if not proj:
        return
    verses = get_verses_for_project(project_id, db_path=DB_PATH)
    update_project(project_id, {"status": ProjectStatus.RENDERING.value}, db_path=DB_PATH)

    chant_worker = ChantWorker()
    vc_worker = VCWorker()

    proj_dir = PROJECTS_DIR / project_id
    takes_dir = proj_dir / "takes"
    takes_dir.mkdir(parents=True, exist_ok=True)

    active_persona_ids = json.loads(proj.get("active_persona_ids_json") or "[]")
    personas = [get_persona(pid, db_path=DB_PATH) for pid in active_persona_ids]
    personas = [p for p in personas if p is not None]
    if not personas:
        personas = list_personas(db_path=DB_PATH)

    render_mode = proj.get("render_mode", "preview_dsp")
    choreo = proj.get("choreography_mode", "AUTO_LITURGICAL")
    reverb_wet = float(proj.get("reverb_wet", 0.15))

    for v in verses:
        # Check if project was paused
        cur_p = get_project(project_id, db_path=DB_PATH)
        if cur_p and cur_p.get("status") == ProjectStatus.PAUSED.value:
            break

        v_idx = v["verse_index"]
        # 1. Synthesize Master Take (C-01)
        take_res = chant_worker.synthesize_verse_takes(
            verse=v,
            num_takes=1,
            nfe=int(proj.get("nfe_steps", 64)),
            cfg=float(proj.get("cfg_strength", 3.0)),
            speed=float(proj.get("chant_speed", 0.90)),
            out_dir=takes_dir,
        )
        master_take = take_res["master_take_path"]
        b_windows = json.loads(take_res["breath_windows_sec_json"] or "[]")
        split_sec = take_res["hemistich_split_sec"]

        # 2. Convert to Pandit Stems
        if render_mode == "studio_seedvc":
            stems = vc_worker.render_studio_seedvc_stems(
                take_wavs=master_take,
                personas=personas,
                out_dir=takes_dir,
                verse_idx=v_idx,
                hemistich_split_sec=split_sec,
            )
        else:
            stems = vc_worker.render_preview_dsp_stems(
                base_take_wav=master_take,
                personas=personas,
                out_dir=takes_dir,
                verse_idx=v_idx,
            )

        # 3. Mix single verse
        mixed_verse_wav = proj_dir / f"v{v_idx:03d}_mixed.wav"
        mix_single_verse(
            stem_paths=stems,
            personas=personas,
            reverb_wet=reverb_wet,
            out_wav=mixed_verse_wav,
            choreography_mode=choreo,
            unit_type=v["unit_type"],
            breath_windows=b_windows,
            hemistich_split_sec=split_sec,
        )

        actual_dur = take_res["actual_duration_sec"]
        update_verse(
            project_id,
            v_idx,
            {
                "mixed_verse_wav_path": str(mixed_verse_wav),
                "actual_duration_sec": actual_dur,
                "qc_status": take_res["qc_status"],
                "qc_notes": take_res["qc_notes"],
                "breath_windows_sec_json": take_res["breath_windows_sec_json"],
                "hemistich_split_sec": split_sec,
            },
            db_path=DB_PATH,
        )

        # Broadcast SSE event
        broadcast_event(
            project_id,
            {
                "type": "verse_completed",
                "verse_index": v_idx,
                "qc_status": take_res["qc_status"],
                "duration_sec": actual_dur,
                "mixed_wav_url": f"/audio/projects/{project_id}/v{v_idx:03d}_mixed.wav",
            },
        )

    # Check status
    cur_p = get_project(project_id, db_path=DB_PATH)
    if cur_p and cur_p.get("status") != ProjectStatus.PAUSED.value:
        update_project(project_id, {"status": ProjectStatus.COMPLETED.value}, db_path=DB_PATH)
        broadcast_event(project_id, {"type": "project_render_finished", "project_id": project_id})


@app.post("/api/projects/{project_id}/render")
def api_render_project(project_id: str, background_tasks: BackgroundTasks) -> Any:
    proj = get_project(project_id, db_path=DB_PATH)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    background_tasks.add_task(_execute_project_render, project_id)
    return {"status": "started", "project_id": project_id}


@app.post("/api/projects/{project_id}/pause")
def api_pause_project(project_id: str) -> Any:
    update_project(project_id, {"status": ProjectStatus.PAUSED.value}, db_path=DB_PATH)
    broadcast_event(project_id, {"type": "project_paused", "project_id": project_id})
    return {"status": "paused", "project_id": project_id}


@app.post("/api/projects/{project_id}/verses/{verse_index}/reroll", response_model=VerseResponse)
def api_reroll_verse(project_id: str, verse_index: int, req: RerollVerseRequest) -> Any:
    verse = get_verse(project_id, verse_index, db_path=DB_PATH)
    if not verse:
        raise HTTPException(status_code=404, detail="Verse not found")

    new_seed = verse["base_seed"] + (req.seed_offset or 101)
    update_verse(project_id, verse_index, {"base_seed": new_seed}, db_path=DB_PATH)
    verse["base_seed"] = new_seed

    proj = get_project(project_id, db_path=DB_PATH)
    active_persona_ids = json.loads(proj.get("active_persona_ids_json") or "[]")
    personas = [get_persona(pid, db_path=DB_PATH) for pid in active_persona_ids]
    personas = [p for p in personas if p is not None] or list_personas(db_path=DB_PATH)

    proj_dir = PROJECTS_DIR / project_id
    takes_dir = proj_dir / "takes"

    # Re-render single verse
    chant_worker = ChantWorker()
    vc_worker = VCWorker()
    take_res = chant_worker.synthesize_verse_takes(
        verse=verse,
        num_takes=1,
        nfe=int(proj.get("nfe_steps", 64)),
        cfg=float(proj.get("cfg_strength", 3.0)),
        speed=float(proj.get("chant_speed", 0.90)),
        out_dir=takes_dir,
    )
    master_take = take_res["master_take_path"]
    b_windows = json.loads(take_res["breath_windows_sec_json"] or "[]")
    split_sec = take_res["hemistich_split_sec"]

    if proj.get("render_mode") == "studio_seedvc":
        stems = vc_worker.render_studio_seedvc_stems(
            take_wavs=master_take,
            personas=personas,
            out_dir=takes_dir,
            verse_idx=verse_index,
            hemistich_split_sec=split_sec,
        )
    else:
        stems = vc_worker.render_preview_dsp_stems(
            base_take_wav=master_take,
            personas=personas,
            out_dir=takes_dir,
            verse_idx=verse_index,
        )

    mixed_verse_wav = proj_dir / f"v{verse_index:03d}_mixed.wav"
    mix_single_verse(
        stem_paths=stems,
        personas=personas,
        reverb_wet=float(proj.get("reverb_wet", 0.15)),
        out_wav=mixed_verse_wav,
        choreography_mode=proj.get("choreography_mode", "AUTO_LITURGICAL"),
        unit_type=verse["unit_type"],
        breath_windows=b_windows,
        hemistich_split_sec=split_sec,
    )

    updated = update_verse(
        project_id,
        verse_index,
        {
            "mixed_verse_wav_path": str(mixed_verse_wav),
            "actual_duration_sec": take_res["actual_duration_sec"],
            "qc_status": take_res["qc_status"],
            "qc_notes": take_res["qc_notes"],
        },
        db_path=DB_PATH,
    )

    broadcast_event(
        project_id,
        {
            "type": "verse_rerolled",
            "verse_index": verse_index,
            "qc_status": take_res["qc_status"],
            "mixed_wav_url": f"/audio/projects/{project_id}/v{verse_index:03d}_mixed.wav",
        },
    )
    return updated


@app.post("/api/projects/{project_id}/master", response_model=MasterExportResponse)
def api_master_project(project_id: str, req: MasterExportRequest) -> Any:
    try:
        res = assemble_project_master(
            project_id=project_id,
            db_path=DB_PATH,
            tanpura_gain_db=req.tanpura_gain_db,
            reverb_wet=req.reverb_wet,
            inter_verse_pause_sec=req.inter_verse_pause_sec,
            section_pause_sec=req.section_pause_sec,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "project_id": project_id,
        "master_wav_url": f"/audio/projects/{project_id}/{project_id}_master_48k_24bit.wav",
        "lrc_url": f"/audio/projects/{project_id}/{project_id}_lyrics.lrc",
        "srt_url": f"/audio/projects/{project_id}/{project_id}_lyrics.srt",
        "stems_zip_url": f"/audio/projects/{project_id}/{project_id}_stems.zip",
        "split_tracks_zip_url": f"/audio/projects/{project_id}/{project_id}_spotify_split_tracks.zip",
        "lufs": res["lufs"],
        "peak_dbtp": res["peak_dbtp"],
    }


@app.post("/api/projects/{project_id}/export-video")
def api_export_video(project_id: str, req: VideoExportRequest) -> Any:
    try:
        res = export_karaoke_video(
            project_id=project_id,
            db_path=DB_PATH,
            font_size=req.font_size,
            bg_color=req.background_color,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "completed",
        "video_mp4_url": f"/audio/projects/{project_id}/{project_id}_karaoke_1080p.mp4",
        "subtitles_ass_url": f"/audio/projects/{project_id}/{project_id}_subtitles.ass",
    }


# ── Server-Sent Events (SSE) ─────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/events")
async def api_project_events(project_id: str, request: Request) -> Any:
    queue: asyncio.Queue = asyncio.Queue()
    if project_id not in _SSE_SUBSCRIBERS:
        _SSE_SUBSCRIBERS[project_id] = []
    _SSE_SUBSCRIBERS[project_id].append(queue)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield json.dumps({"type": "connected", "project_id": project_id})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield data
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "ping"})
        finally:
            if project_id in _SSE_SUBSCRIBERS and queue in _SSE_SUBSCRIBERS[project_id]:
                _SSE_SUBSCRIBERS[project_id].remove(queue)

    return EventSourceResponse(event_generator())


# ── Personas Endpoints ───────────────────────────────────────────────────────

@app.get("/api/personas", response_model=List[PersonaResponse])
def api_list_personas() -> Any:
    return list_personas(db_path=DB_PATH)


@app.post("/api/personas/forge", response_model=PersonaResponse)
def api_forge_persona(req: PersonaCreateRequest) -> Any:
    p_id = f"pandit_{uuid.uuid4().hex[:6]}"
    raw_wav = PERSONAS_DIR / f"{p_id}_raw.wav"
    ref_wav = PERSONAS_DIR / f"{p_id}_ref.wav"
    tensors_pt = PERSONAS_DIR / f"{p_id}_tensors.pt"

    generate_parler_reference(
        prompt=req.prompt or f"A classical Vedic pandit, {req.role_tag}",
        out_wav_path=raw_wav,
    )
    sculpt_vocal_tract(
        in_wav=raw_wav,
        out_wav=ref_wav,
        formant_shift_st=req.formant_shift_st,
        chest_db=req.chest_db,
        presence_db=req.presence_db,
        air_db=req.air_db,
    )
    extract_and_cache_seedvc_tensors(
        ref_wav_path=ref_wav,
        out_pt_path=tensors_pt,
    )
    if raw_wav.exists():
        raw_wav.unlink()

    recipe = {
        "formant_shift_st": req.formant_shift_st,
        "chest_db": req.chest_db,
        "presence_db": req.presence_db,
        "air_db": req.air_db,
        "prompt": req.prompt,
    }
    persona_data = {
        "id": p_id,
        "name": req.name,
        "role_tag": req.role_tag,
        "creation_mode": "PARLER_FORGED",
        "recipe_json": json.dumps(recipe),
        "ref_wav_path": str(ref_wav),
        "cached_tensors_path": str(tensors_pt),
        "default_pan": req.default_pan,
        "default_gain_db": req.default_gain_db,
    }
    return create_persona(persona_data, db_path=DB_PATH)


@app.post("/api/personas/blend", response_model=PersonaResponse)
def api_blend_personas(req: PersonaBlendRequest) -> Any:
    p_a = get_persona(req.parent_a_id, db_path=DB_PATH)
    p_b = get_persona(req.parent_b_id, db_path=DB_PATH)
    if not p_a or not p_b:
        raise HTTPException(status_code=404, detail="Parent persona not found")

    p_id = f"pandit_blend_{uuid.uuid4().hex[:6]}"
    tensors_pt = PERSONAS_DIR / f"{p_id}_tensors.pt"
    ref_wav = PERSONAS_DIR / f"{p_id}_ref.wav"

    # Blend tensors
    blend_personas(
        persona_a_pt=p_a["cached_tensors_path"],
        persona_b_pt=p_b["cached_tensors_path"],
        alpha=req.alpha,
        out_pt_path=tensors_pt,
    )

    # Use parent A's ref wav or copy
    shutil.copy(p_a["ref_wav_path"], str(ref_wav))

    persona_data = {
        "id": p_id,
        "name": req.name,
        "role_tag": req.role_tag,
        "creation_mode": f"SLERP_BLEND_{req.parent_a_id}_{req.parent_b_id}",
        "recipe_json": json.dumps({"parent_a": req.parent_a_id, "parent_b": req.parent_b_id, "alpha": req.alpha}),
        "ref_wav_path": str(ref_wav),
        "cached_tensors_path": str(tensors_pt),
        "default_pan": req.default_pan,
        "default_gain_db": req.default_gain_db,
    }
    return create_persona(persona_data, db_path=DB_PATH)


# ── Audio Static File Server with HTTP Range Support ─────────────────────────

@app.get("/audio/{file_path:path}")
async def serve_audio_file(file_path: str, request: Request) -> Response:
    """Streams audio files with HTTP Range header support for WaveSurfer.js."""
    target_path = STORAGE_DIR / file_path
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    file_size = target_path.stat().st_size
    range_header = request.headers.get("range")

    content_type = "audio/wav"
    if target_path.suffix == ".flac":
        content_type = "audio/flac"
    elif target_path.suffix == ".mp4":
        content_type = "video/mp4"
    elif target_path.suffix in (".srt", ".lrc", ".ass"):
        content_type = "text/plain; charset=utf-8"
    elif target_path.suffix == ".zip":
        content_type = "application/zip"

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = end - start + 1

        def file_iterator():
            with open(target_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk_size = min(64 * 1024, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            file_iterator(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": content_type,
            },
        )

    return FileResponse(path=str(target_path), media_type=content_type)
