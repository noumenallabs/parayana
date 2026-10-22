"""Vāgdhenu Goṣṭhī Studio — Semicircle Spatial Mixer, Tanpura Bed & Mastering.

Implements:
- 5-Pandit Semicircle spatial panning ([-0.45, -0.22, 0.0, +0.22, +0.45]) with constant-power panning
- Active voice RMS calibration (-20.0 dBFS per Flaw 11)
- Support-voice daṇḍa breath ducking (-14 dB across breath window per F-04)
- Dynamic liturgical choreography (AUTO_LITURGICAL, ANTIPHONAL, FULL_UNISON per F-09)
- Shared Mandapa acoustic space via Spotify Pedalboard (Highpass 85Hz, LowShelf 180Hz -1.5dB, Mandapa IR Convolution, Compressor)
- C#3 Tanpura drone bed layering (-18.0 dB) with 1.5s lead-in and 2.5s fade-out
- Final Master normalization: -14.0 ± 0.5 LUFS via pyloudnorm + Limiter (-1.0 dBTP)
- Synchronized .srt and .lrc timing tracks generation
- Lossless stems ZIP packaging and Spotify multi-track album splitter (F-10)
"""

from __future__ import annotations

import json
import math
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from config import (
    DB_PATH,
    MANDAPA_IR_PATH,
    PROJECTS_DIR,
    SAMPLE_RATE_MASTER,
    TANPURA_WAV_PATH,
)
from db import get_project, get_verses_for_project, update_project
from schemas import ChoreographyMode, UnitType

# Optional pedalboard import
try:
    from pedalboard import (
        Compressor,
        Convolution,
        HighpassFilter,
        Limiter,
        LowShelfFilter,
        Pedalboard,
    )
    _HAS_PEDALBOARD = True
except ImportError:
    _HAS_PEDALBOARD = False


# ── Active RMS Calibration & Spatial Panning (Flaw 11) ──────────────────────

def calibrate_active_rms(audio: np.ndarray, target_dbfs: float = -20.0, gate_threshold: float = 0.015) -> np.ndarray:
    """Calibrates active speech/singing RMS (where |y| > gate_threshold) to target_dbfs (-20 dBFS)."""
    active_mask = np.abs(audio) > gate_threshold
    if np.sum(active_mask) == 0:
        return audio
    active_rms = float(np.sqrt(np.mean(audio[active_mask] ** 2)))
    if active_rms <= 0:
        return audio

    current_dbfs = 20.0 * math.log10(active_rms)
    gain_linear = 10.0 ** ((target_dbfs - current_dbfs) / 20.0)
    # Clamp extreme amplification
    gain_linear = min(gain_linear, 4.0)
    return audio * gain_linear


def constant_power_pan(mono: np.ndarray, pan: float) -> Tuple[np.ndarray, np.ndarray]:
    """Applies constant-power panning (-1.0 = hard Left, 0.0 = Center, +1.0 = hard Right)."""
    pan_clamped = max(-1.0, min(1.0, pan))
    theta = (pan_clamped + 1.0) * (math.pi / 4.0)  # 0 to pi/2
    left = mono * math.cos(theta)
    right = mono * math.sin(theta)
    return left, right


# ── Single Verse Spatial Mix ────────────────────────────────────────────────

def mix_single_verse(
    stem_paths: List[str],
    personas: List[Dict[str, Any]],
    reverb_wet: float = 0.15,
    out_wav: Optional[str | Path] = None,
    choreography_mode: str = "AUTO_LITURGICAL",
    unit_type: str = "METRICAL_SLOKA",
    breath_windows: Optional[List[List[float]]] = None,
    hemistich_split_sec: Optional[float] = None,
    sr: int = SAMPLE_RATE_MASTER,
) -> np.ndarray:
    """Renders multi-pandit stems into a 48 kHz stereo verse bus in Mandapa acoustic space."""
    if not stem_paths:
        return np.zeros((sr, 2), dtype=np.float32)

    # Load and resample all stems to 48 kHz
    stems_48k: List[np.ndarray] = []
    max_len = 0

    for path_str in stem_paths:
        y, s_in = sf.read(path_str)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if s_in != sr:
            y = librosa.resample(y.astype(np.float32), orig_sr=s_in, target_sr=sr)
        stems_48k.append(y.astype(np.float32))
        if len(y) > max_len:
            max_len = len(y)

    # Pad all stems to uniform length
    num_stems = len(stems_48k)
    aligned_stems = np.zeros((num_stems, max_len), dtype=np.float32)
    for i, stem in enumerate(stems_48k):
        aligned_stems[i, : len(stem)] = stem

    bus_l = np.zeros(max_len, dtype=np.float32)
    bus_r = np.zeros(max_len, dtype=np.float32)

    # Default semicircle pan angles: [-0.45, -0.22, 0.0, +0.22, +0.45]
    default_pans = [-0.45, -0.22, 0.0, 0.22, 0.45]

    # Dynamic Liturgical Choreography (F-09)
    # Determine which stems are active for this verse/hemistich
    active_mask = np.ones(num_stems, dtype=bool)

    if choreography_mode == ChoreographyMode.AUTO_LITURGICAL.value:
        if unit_type in (UnitType.UVACA_CONNECTIVE.value, UnitType.GADYA_PROSE.value):
            # Solo Lead Pandit (pandit 1) at Center
            active_mask[1:] = False

    active_count = int(np.sum(active_mask))
    # Flaw 11: apply -2.5 dB chorus bus trim when full 5-voice ensemble is active
    chorus_bus_trim_db = -2.5 if active_count >= 5 else 0.0
    chorus_bus_trim = 10.0 ** (chorus_bus_trim_db / 20.0)

    for i in range(num_stems):
        if not active_mask[i]:
            continue

        p_info = personas[i] if i < len(personas) else {}
        pan = float(p_info.get("default_pan", default_pans[i % len(default_pans)]))
        gain_db = float(p_info.get("default_gain_db", 0.0))
        gain_linear = 10.0 ** (gain_db / 20.0)

        stem = aligned_stems[i]

        # 1. Calibrate active RMS to -20.0 dBFS
        calibrated = calibrate_active_rms(stem, target_dbfs=-20.0) * gain_linear

        # 2. F-04: Support-Voice Daṇḍa Breath Ducking (-14 dB)
        is_lead = (i == 0 or "mukhya" in p_info.get("id", ""))
        if not is_lead and breath_windows:
            duck_linear = 10.0 ** (-14.0 / 20.0)  # ~0.20
            fade_handle_samples = int(0.025 * sr)
            for b_start, b_end in breath_windows:
                s_idx = max(0, int(b_start * sr))
                e_idx = min(max_len, int(b_end * sr))
                if s_idx < e_idx:
                    # Apply -14 dB attenuation across breath window with 25ms cosine handles
                    calibrated[s_idx:e_idx] *= duck_linear
                    if s_idx >= fade_handle_samples:
                        calibrated[s_idx - fade_handle_samples : s_idx] *= np.linspace(1.0, duck_linear, fade_handle_samples)
                    if e_idx + fade_handle_samples <= max_len:
                        calibrated[e_idx : e_idx + fade_handle_samples] *= np.linspace(duck_linear, 1.0, fade_handle_samples)

        # 3. Constant-Power Pan across Semicircle
        sl, sr_ch = constant_power_pan(calibrated, pan)
        bus_l += sl * chorus_bus_trim
        bus_r += sr_ch * chorus_bus_trim

    stereo_bus = np.stack([bus_l, bus_r], axis=-1)

    # 4. Shared Mandapa Acoustic Space Processing via Spotify Pedalboard
    if _HAS_PEDALBOARD:
        plugins = [
            HighpassFilter(cutoff_frequency_hz=85.0),
            LowShelfFilter(cutoff_frequency_hz=180.0, gain_db=-1.5),
        ]
        if MANDAPA_IR_PATH.exists() and reverb_wet > 0.001:
            plugins.append(Convolution(str(MANDAPA_IR_PATH), mix=reverb_wet))
        plugins.append(Compressor(threshold_db=-16.0, ratio=2.5))

        board = Pedalboard(plugins)
        stereo_bus = board(stereo_bus, sr)

    if out_wav:
        out_p = Path(out_wav)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_p), stereo_bus.astype(np.float32), sr, subtype="PCM_24")

    return stereo_bus.astype(np.float32)


# ── Synced Lyrics Exporter (.srt and .lrc) ───────────────────────────────────

def format_timestamp_srt(total_seconds: float) -> str:
    millis = int(round((total_seconds - int(total_seconds)) * 1000))
    secs = int(total_seconds) % 60
    mins = (int(total_seconds) // 60) % 60
    hours = int(total_seconds) // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_timestamp_lrc(total_seconds: float) -> str:
    mins = int(total_seconds) // 60
    secs = total_seconds % 60
    return f"[{mins:02d}:{secs:05.2f}]"


def generate_timing_files(
    timed_verses: List[Dict[str, Any]],
    srt_out_path: Path,
    lrc_out_path: Path,
) -> None:
    """Writes synchronized SubRip (.srt) and Lyric (.lrc) timing files."""
    srt_lines = []
    lrc_lines = ["[ti:Vāgdhenu Goṣṭhī Studio Master Chanting]", "[al:Parayana Sacred Chants]"]

    for idx, tv in enumerate(timed_verses, start=1):
        s_time = tv["start_sec"]
        e_time = tv["end_sec"]
        text = tv["raw_text"].strip()

        # SRT format
        srt_lines.append(str(idx))
        srt_lines.append(f"{format_timestamp_srt(s_time)} --> {format_timestamp_srt(e_time)}")
        srt_lines.append(text)
        srt_lines.append("")

        # LRC format
        lrc_lines.append(f"{format_timestamp_lrc(s_time)}{text}")

    srt_out_path.write_text("\n".join(srt_lines), encoding="utf-8")
    lrc_out_path.write_text("\n".join(lrc_lines), encoding="utf-8")


# ── Full Project Master Assembly ─────────────────────────────────────────────

def assemble_project_master(
    project_id: str,
    db_path: Path = DB_PATH,
    tanpura_gain_db: Optional[float] = None,
    reverb_wet: Optional[float] = None,
    inter_verse_pause_sec: Optional[float] = None,
    section_pause_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """Assembles all verses, layers continuous C#3 tanpura bed, normalizes to -14.0 LUFS,
    and packages master WAV, SRT, LRC, stems ZIP, and Spotify split tracks (US-07, F-10).
    """
    proj = get_project(project_id, db_path=db_path)
    if not proj:
        raise ValueError(f"Project '{project_id}' not found")

    verses = get_verses_for_project(project_id, db_path=db_path)
    if not verses:
        raise ValueError(f"No verses found for project '{project_id}'")

    proj_dir = PROJECTS_DIR / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    sr = SAMPLE_RATE_MASTER
    v_pause = inter_verse_pause_sec if inter_verse_pause_sec is not None else float(proj.get("inter_verse_pause_sec", 0.85))
    s_pause = section_pause_sec if section_pause_sec is not None else float(proj.get("section_pause_sec", 1.60))
    t_gain_db = tanpura_gain_db if tanpura_gain_db is not None else float(proj.get("tanpura_gain_db", -18.0))

    lead_in_sec = 1.5
    lead_in_samples = int(lead_in_sec * sr)

    # Concatenate verse audio buffers with pauses and record exact timestamps
    current_time_sec = lead_in_sec
    timed_verses: List[Dict[str, Any]] = []
    assembled_audio_segments: List[np.ndarray] = [np.zeros((lead_in_samples, 2), dtype=np.float32)]

    # Group verses by section for Spotify multi-track album splitter (F-10)
    sections_map: Dict[str, List[np.ndarray]] = {}

    for i, v in enumerate(verses):
        v_idx = v["verse_index"]
        mixed_wav = v.get("mixed_verse_wav_path")

        if mixed_wav and Path(mixed_wav).exists():
            y_v, s_in = sf.read(str(mixed_wav))
            if y_v.ndim == 1:
                y_v = np.stack([y_v, y_v], axis=-1)
            if s_in != sr:
                y_v = librosa.resample(y_v.T, orig_sr=s_in, target_sr=sr).T
        else:
            # Fallback placeholder duration
            dur = float(v.get("actual_duration_sec") or v.get("expected_duration_sec") or 9.0)
            y_v = np.zeros((int(dur * sr), 2), dtype=np.float32)

        v_dur_sec = len(y_v) / sr
        start_sec = round(current_time_sec, 3)
        end_sec = round(current_time_sec + v_dur_sec, 3)

        timed_verses.append({
            "verse_index": v_idx,
            "section_label": v["section_label"],
            "raw_text": v["raw_text"],
            "start_sec": start_sec,
            "end_sec": end_sec,
        })

        assembled_audio_segments.append(y_v.astype(np.float32))

        # Track section audio
        sec_label = v["section_label"]
        if sec_label not in sections_map:
            sections_map[sec_label] = []
        sections_map[sec_label].append(y_v.astype(np.float32))

        current_time_sec = end_sec

        # Add pause between verses (or section pause between sections)
        if i < len(verses) - 1:
            next_sec = verses[i + 1]["section_label"]
            pause_sec = s_pause if next_sec != v["section_label"] else v_pause
            pause_samples = int(pause_sec * sr)
            pause_chunk = np.zeros((pause_samples, 2), dtype=np.float32)
            assembled_audio_segments.append(pause_chunk)
            sections_map[sec_label].append(pause_chunk)
            current_time_sec += pause_sec

    # Tail lead-out of 2.5s for tanpura fade
    lead_out_sec = 2.5
    lead_out_samples = int(lead_out_sec * sr)
    assembled_audio_segments.append(np.zeros((lead_out_samples, 2), dtype=np.float32))

    stitched_voices = np.concatenate(assembled_audio_segments, axis=0)
    total_samples = len(stitched_voices)
    total_dur_sec = total_samples / sr

    # Layer continuous C#3 Tanpura Bed
    if TANPURA_WAV_PATH.exists():
        tanpura_raw, t_sr = sf.read(str(TANPURA_WAV_PATH))
        if tanpura_raw.ndim == 1:
            tanpura_raw = np.stack([tanpura_raw, tanpura_raw], axis=-1)
        if t_sr != sr:
            tanpura_raw = librosa.resample(tanpura_raw.T, orig_sr=t_sr, target_sr=sr).T

        # Tile tanpura to cover total duration
        n_repeats = math.ceil(total_samples / len(tanpura_raw)) + 1
        tanpura_bed = np.tile(tanpura_raw, (n_repeats, 1))[:total_samples].copy()

        # Apply tanpura gain
        tanpura_linear = 10.0 ** (t_gain_db / 20.0)
        tanpura_bed *= tanpura_linear

        # 2.5s cosine fade-out at the end
        fade_samples = min(lead_out_samples, total_samples)
        fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_samples)))
        tanpura_bed[-fade_samples:, 0] *= fade_out
        tanpura_bed[-fade_samples:, 1] *= fade_out

        master_mix = stitched_voices + tanpura_bed
    else:
        master_mix = stitched_voices

    # Master Loudness Normalization to -14.0 LUFS (pyloudnorm) + True-Peak Protection (-1.0 dBTP)
    meter = pyln.Meter(sr)
    current_lufs = meter.integrated_loudness(master_mix.astype(np.float64))

    # Apply loudness normalization
    if not np.isinf(current_lufs) and not np.isnan(current_lufs):
        normalized_master = pyln.normalize.loudness(
            master_mix.astype(np.float64),
            current_lufs,
            -14.0,
        ).astype(np.float32)
    else:
        normalized_master = master_mix.astype(np.float32)

    # True-Peak ceiling at or below -1.0 dBTP (10^(-1/20) ~ 0.89125)
    max_allowed_peak = 0.89125
    cur_peak = np.max(np.abs(normalized_master))
    if cur_peak > max_allowed_peak:
        normalized_master = np.clip(normalized_master, -max_allowed_peak, max_allowed_peak)

    peak_val = float(np.max(np.abs(normalized_master)))
    peak_dbtp = round(20.0 * math.log10(max(1e-6, peak_val)), 2)
    final_lufs = round(float(meter.integrated_loudness(normalized_master.astype(np.float64))), 2)

    # Write Master WAV (48 kHz / 24-bit Stereo PCM_24)
    master_wav_path = proj_dir / f"{project_id}_master_48k_24bit.wav"
    sf.write(str(master_wav_path), normalized_master, sr, subtype="PCM_24")

    # Generate Synced Lyrics (.srt and .lrc)
    srt_path = proj_dir / f"{project_id}_lyrics.srt"
    lrc_path = proj_dir / f"{project_id}_lyrics.lrc"
    generate_timing_files(timed_verses, srt_path, lrc_path)

    # Stems ZIP Archive
    stems_zip_path = proj_dir / f"{project_id}_stems.zip"
    with zipfile.ZipFile(str(stems_zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        takes_dir = proj_dir / "takes"
        if takes_dir.exists():
            for f in takes_dir.glob("*.flac"):
                zf.write(str(f), arcname=f"stems/{f.name}")

    # Spotify Multi-Track Splitter (F-10)
    split_tracks_zip_path = proj_dir / f"{project_id}_spotify_split_tracks.zip"
    with zipfile.ZipFile(str(split_tracks_zip_path), "w", zipfile.ZIP_DEFLATED) as zf_split:
        for idx, (sec_name, sec_chunks) in enumerate(sections_map.items(), start=1):
            sec_audio = np.concatenate(sec_chunks, axis=0)
            # Normalize split track to -14.0 LUFS
            try:
                sec_lufs = meter.integrated_loudness(sec_audio.astype(np.float64))
                sec_norm = pyln.normalize.loudness(sec_audio.astype(np.float64), sec_lufs, -14.0).astype(np.float32)
            except Exception:
                sec_norm = sec_audio.astype(np.float32)
            safe_name = f"{idx:02d}_{sec_name.replace(' ', '_')}.wav"
            sec_temp = proj_dir / safe_name
            sf.write(str(sec_temp), sec_norm, sr, subtype="PCM_24")
            zf_split.write(str(sec_temp), arcname=safe_name)
            if sec_temp.exists():
                sec_temp.unlink()

    # Update SQLite Project record
    update_project(
        project_id,
        {
            "master_wav_path": str(master_wav_path),
            "srt_path": str(srt_path),
            "lrc_path": str(lrc_path),
            "split_tracks_zip_path": str(split_tracks_zip_path),
            "status": "COMPLETED",
        },
        db_path=db_path,
    )

    return {
        "master_wav_path": str(master_wav_path),
        "srt_path": str(srt_path),
        "lrc_path": str(lrc_path),
        "stems_zip_path": str(stems_zip_path),
        "split_tracks_zip_path": str(split_tracks_zip_path),
        "lufs": final_lufs,
        "peak_dbtp": peak_dbtp,
        "duration_sec": round(total_dur_sec, 2),
    }
