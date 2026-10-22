"""Vāgdhenu Goṣṭhī Studio — System Configuration & Environment Setup.

Registers vendor modules on sys.path, defines absolute storage and model weight
paths, configures Apple Silicon (mps) mixed-precision discipline, and exports
tonic acoustic invariants.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
import torch

# ── Apple Silicon (mps) Mixed-Precision Discipline ──────────────────────────
# Setting PYTORCH_ENABLE_MPS_FALLBACK=1 prevents CPU aborts on un-implemented MPS kernels
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# ── Directory Layout ────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

STORAGE_DIR = BACKEND_DIR / "storage"
DB_PATH = STORAGE_DIR / "studio.db"

WEIGHTS_DIR = STORAGE_DIR / "weights"
VAGDHENU_WEIGHTS_DIR = WEIGHTS_DIR / "vagdhenu"
SEEDVC_WEIGHTS_DIR = WEIGHTS_DIR / "seedvc"
PERSONAS_DIR = STORAGE_DIR / "personas"
ACOUSTICS_DIR = STORAGE_DIR / "acoustics"
PROJECTS_DIR = STORAGE_DIR / "projects"

VENDOR_DIR = BACKEND_DIR / "vendor"
VAGDHENU_DIR = VENDOR_DIR / "vagdhenu"
VAGDHENU_SRC = VAGDHENU_DIR / "src"
BIGVGAN_DIR = VENDOR_DIR / "BigVGAN"
SEEDVC_DIR = VENDOR_DIR / "seed-vc"
INDICF5_DIR = VENDOR_DIR / "IndicF5"

# ── Acoustic Reference Paths ────────────────────────────────────────────────
TANPURA_WAV_PATH = ACOUSTICS_DIR / "csharp3_tanpura_48k.wav"
MANDAPA_IR_PATH = ACOUSTICS_DIR / "temple_mandapa_ir_48k.wav"

# ── Weight File Paths ───────────────────────────────────────────────────────
VAGDHENU_STEER_WEIGHTS = VAGDHENU_WEIGHTS_DIR / "voice_steer_ema_2026-06-17.pt"
VAGDHENU_ARMA_WEIGHTS = VAGDHENU_WEIGHTS_DIR / "voice_armA_ema_2026-06-11.pt"
VAGDHENU_VOC_WEIGHTS = VAGDHENU_WEIGHTS_DIR / "voc_bigvgan_EMA_2026-06-11.pth"
VAGDHENU_VOCAB = VAGDHENU_WEIGHTS_DIR / "vocab.txt"

SEEDVC_DIT_WEIGHTS = SEEDVC_WEIGHTS_DIR / "DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth"
SEEDVC_RMVPE_WEIGHTS = SEEDVC_WEIGHTS_DIR / "rmvpe.pt"
SEEDVC_CAMPPLUS_WEIGHTS = SEEDVC_WEIGHTS_DIR / "campplus_cn_common.bin"

# ── Acoustic & Liturgical Invariants ────────────────────────────────────────
TONIC_CSHARP3_HZ = 138.5913     # ādhāra-ṣaḍja (C#3)
DOMINANT_GSHARP3_HZ = 207.6523  # pañcama (G#3)
OCTAVE_CSHARP4_HZ = 277.1826    # tāra-ṣaḍja (C#4)
LOWER_CSHARP2_HZ = 69.2956      # mandra-ṣaḍja (C#2)

SAMPLE_RATE_MASTER = 48000
SAMPLE_RATE_SEEDVC = 44100
SAMPLE_RATE_VAGDHENU = 24000

MASTER_LUFS_TARGET = -14.0
MASTER_TRUE_PEAK_DBTP = -1.0

# ── Flaw 10: Global Apple Metal Concurrency Lock ────────────────────────────
# Guard all torch.device("mps") / neural forward passes across workers to avoid
# command buffer crashes when background renders race with foreground auditions.
MPS_LOCK = threading.Lock()

# ── Device Resolution ───────────────────────────────────────────────────────
def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

DEVICE = get_device()

# ── Register Vendor Paths on sys.path ───────────────────────────────────────
for p in (VAGDHENU_SRC, BIGVGAN_DIR, SEEDVC_DIR, INDICF5_DIR):
    str_p = str(p)
    if p.exists() and str_p not in sys.path:
        sys.path.insert(0, str_p)

# Ensure storage directories exist
for d in (STORAGE_DIR, WEIGHTS_DIR, VAGDHENU_WEIGHTS_DIR, SEEDVC_WEIGHTS_DIR,
          PERSONAS_DIR, ACOUSTICS_DIR, PROJECTS_DIR):
    d.mkdir(parents=True, exist_ok=True)
