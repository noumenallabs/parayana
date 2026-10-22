"""Vāgdhenu Goṣṭhī Studio — Pydantic v2 Contracts & Schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UnitType(str, Enum):
    METRICAL_SLOKA = "METRICAL_SLOKA"
    UVACA_CONNECTIVE = "UVACA_CONNECTIVE"
    NAMAVALI_108 = "NAMAVALI_108"
    GADYA_PROSE = "GADYA_PROSE"
    JAPA_REPEAT = "JAPA_REPEAT"
    REFRAIN_HOOK = "REFRAIN_HOOK"


class ChoreographyMode(str, Enum):
    AUTO_LITURGICAL = "AUTO_LITURGICAL"
    ANTIPHONAL_CALL_RESPONSE = "ANTIPHONAL_CALL_RESPONSE"
    FULL_UNISON = "FULL_UNISON"


class RenderMode(str, Enum):
    PREVIEW_DSP = "preview_dsp"
    STUDIO_SEEDVC = "studio_seedvc"


class QCStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    SILENCE_FLAG = "SILENCE_FLAG"
    DURATION_FLAG = "DURATION_FLAG"


class ProjectStatus(str, Enum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"


# ── Persona Schemas ──────────────────────────────────────────────────────────

class PersonaCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    role_tag: str = Field(..., max_length=50, description="Lead Center, Deep Elder, etc.")
    prompt: Optional[str] = Field(None, description="Parler-TTS prompt description")
    formant_shift_st: float = Field(0.0, ge=-2.5, le=2.5)
    chest_db: float = Field(0.0, ge=-12.0, le=12.0)
    presence_db: float = Field(0.0, ge=-12.0, le=12.0)
    air_db: float = Field(0.0, ge=-12.0, le=12.0)
    default_pan: float = Field(0.0, ge=-1.0, le=1.0)
    default_gain_db: float = Field(0.0, ge=-24.0, le=12.0)


class PersonaBlendRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    role_tag: str = Field("Blended Voice", max_length=50)
    parent_a_id: str
    parent_b_id: str
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="0.0 = 100% Parent A, 1.0 = 100% Parent B")
    default_pan: float = Field(0.0, ge=-1.0, le=1.0)
    default_gain_db: float = Field(0.0, ge=-24.0, le=12.0)


class PersonaResponse(BaseModel):
    id: str
    name: str
    role_tag: str
    creation_mode: str
    recipe_json: Optional[str] = None
    ref_wav_path: str
    cached_tensors_path: str
    default_pan: float = 0.0
    default_gain_db: float = 0.0
    created_at: Optional[str] = None


# ── Verse Schemas ────────────────────────────────────────────────────────────

class VerseResponse(BaseModel):
    id: str
    project_id: str
    verse_index: int
    section_label: str
    unit_type: UnitType
    choreography_override: Optional[str] = None
    raw_text: str
    kannada_text: str
    slp1_text: str
    iast_text: Optional[str] = None
    lg_signature: Optional[str] = None
    syllable_count: int = 0
    detected_meter: Optional[str] = None
    override_meter: Optional[str] = None
    apply_internal_sandhi: bool = True
    base_seed: int = 100
    hemistich_split_sec: Optional[float] = None
    breath_windows_sec_json: Optional[str] = "[]"
    expected_duration_sec: Optional[float] = None
    actual_duration_sec: Optional[float] = None
    qc_status: QCStatus = QCStatus.PENDING
    qc_notes: Optional[str] = None
    mixed_verse_wav_path: Optional[str] = None


class VerseUpdateRequest(BaseModel):
    override_meter: Optional[str] = None
    choreography_override: Optional[str] = None
    apply_internal_sandhi: Optional[bool] = None
    base_seed: Optional[int] = None


class RerollVerseRequest(BaseModel):
    seed_offset: Optional[int] = 101


# ── Project Schemas ──────────────────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    raw_input_text: str = Field(..., min_length=1)
    japa_repeat_count: Optional[int] = Field(None, description="11, 21, 54, or 108 for japa repetition mode")
    render_mode: RenderMode = RenderMode.PREVIEW_DSP
    active_persona_ids: List[str] = Field(default_factory=list)
    chant_speed: float = Field(0.90, ge=0.5, le=1.5)
    nfe_steps: int = Field(64, ge=16, le=128)
    cfg_strength: float = Field(3.0, ge=1.0, le=7.0)
    tanpura_gain_db: float = Field(-18.0, ge=-40.0, le=0.0)
    reverb_wet: float = Field(0.15, ge=0.0, le=0.60)
    inter_verse_pause_sec: float = Field(0.85, ge=0.1, le=5.0)
    section_pause_sec: float = Field(1.60, ge=0.5, le=10.0)
    choreography_mode: ChoreographyMode = ChoreographyMode.AUTO_LITURGICAL
    retain_intermediate_stems: bool = False


class ProjectDetailResponse(BaseModel):
    id: str
    title: str
    raw_input_text: str
    render_mode: RenderMode
    active_persona_ids: List[str]
    chant_speed: float
    nfe_steps: int
    cfg_strength: float
    tanpura_gain_db: float
    reverb_wet: float
    inter_verse_pause_sec: float
    section_pause_sec: float
    choreography_mode: ChoreographyMode
    retain_intermediate_stems: bool
    status: ProjectStatus
    master_wav_path: Optional[str] = None
    lrc_path: Optional[str] = None
    srt_path: Optional[str] = None
    split_tracks_zip_path: Optional[str] = None
    video_mp4_path: Optional[str] = None
    created_at: Optional[str] = None
    verses: List[VerseResponse] = Field(default_factory=list)


class MasterExportRequest(BaseModel):
    tanpura_gain_db: Optional[float] = None
    reverb_wet: Optional[float] = None
    inter_verse_pause_sec: Optional[float] = None
    section_pause_sec: Optional[float] = None


class MasterExportResponse(BaseModel):
    project_id: str
    master_wav_url: str
    lrc_url: str
    srt_url: str
    stems_zip_url: Optional[str] = None
    split_tracks_zip_url: Optional[str] = None
    lufs: float
    peak_dbtp: float


class VideoExportRequest(BaseModel):
    font_name: Optional[str] = None
    font_size: int = Field(38, ge=20, le=80)
    background_color: str = "#0F1117"
    highlight_color: str = "#FFB300"
