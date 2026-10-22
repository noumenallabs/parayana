#!/usr/bin/env bash
# Vāgdhenu Goṣṭhī Studio — macOS Apple Silicon (M3 Pro) Setup Bootstrap
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$BACKEND_DIR")"

echo "=== Vāgdhenu Goṣṭhī Studio Setup (M3 Pro / macOS Apple Silicon) ==="

cd "$BACKEND_DIR"

# 1. Python 3.10 Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating Python 3.10 virtual environment..."
    python3.10 -m venv .venv || python3 -m venv .venv
fi

source .venv/bin/activate

# 2. Upgrade pip and install PyTorch with MPS support
echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3. Setup Vendor Repositories
mkdir -p vendor
export GIT_TERMINAL_PROMPT=0

if [ ! -d "vendor/vagdhenu" ]; then
    echo "Cloning prathoshap/vagdhenu..."
    git clone --depth 1 https://github.com/prathoshap/vagdhenu.git vendor/vagdhenu
fi

if [ ! -d "vendor/IndicF5" ]; then
    echo "Cloning AI4Bharat/IndicF5..."
    git clone --depth 1 https://github.com/AI4Bharat/IndicF5.git vendor/IndicF5
    pip install -e vendor/IndicF5 --no-deps || true
fi

if [ ! -d "vendor/BigVGAN" ]; then
    echo "Cloning NVIDIA/BigVGAN..."
    git clone --depth 1 https://github.com/NVIDIA/BigVGAN.git vendor/BigVGAN
fi

if [ ! -d "vendor/seed-vc" ]; then
    echo "Cloning Plachtaa/seed-vc..."
    git clone --depth 1 https://github.com/Plachtaa/seed-vc.git vendor/seed-vc
fi

# 4. Create Storage Dirs
mkdir -p storage/weights/vagdhenu storage/weights/seedvc storage/personas storage/acoustics storage/projects

# 5. Download Model Checkpoints from Hugging Face if not present
echo "Downloading / Verifying Vāgdhenu checkpoints..."
python -c '
from huggingface_hub import hf_hub_download
from pathlib import Path
target_dir = Path("storage/weights/vagdhenu")
target_dir.mkdir(parents=True, exist_ok=True)
files = [
    "voice_steer_ema_2026-06-17.pt",
    "voice_armA_ema_2026-06-11.pt",
    "voc_bigvgan_EMA_2026-06-11.pth",
    "vocab.txt"
]
for f in files:
    dest = target_dir / f
    if not dest.exists():
        print(f"Downloading {f} from prathoshap/vagdhenu...")
        hf_hub_download(repo_id="prathoshap/vagdhenu", filename=f, local_dir=str(target_dir))
    else:
        print(f"Found existing {f}")
'

# 6. Synthesize Acoustic References
echo "Synthesizing acoustic references (C#3 Tanpura & Temple Mandapa IR)..."
python scripts/generate_acoustics.py

echo "=== Setup Complete! Run 'python tests/verify_us01_env.py' to verify. ==="
