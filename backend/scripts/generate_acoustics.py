"""Vāgdhenu Goṣṭhī Studio — Acoustic Reference Generator.

Synthesizes:
1. csharp3_tanpura_48k.wav: A phase-continuous, 60-second stereo 48 kHz
   Sa–Pa–Sa tanpura drone locked to 138.5913 Hz (C#3) and 207.6523 Hz (G#3).
2. temple_mandapa_ir_48k.wav: A stereo impulse response simulating a stone
   temple maṇḍapa with an RT60 of 1.35 seconds.
"""

from __future__ import annotations

import math
import numpy as np
import soundfile as sf
from pathlib import Path
import sys

# Ensure config is importable
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import (
    ACOUSTICS_DIR,
    TANPURA_WAV_PATH,
    MANDAPA_IR_PATH,
    TONIC_CSHARP3_HZ,
    DOMINANT_GSHARP3_HZ,
    OCTAVE_CSHARP4_HZ,
    SAMPLE_RATE_MASTER,
)


def synthesize_tanpura_drone(
    duration_sec: float = 60.0,
    sr: int = SAMPLE_RATE_MASTER,
) -> np.ndarray:
    """Synthesizes a 60-second 48 kHz stereo tanpura drone in C#3 (138.5913 Hz).

    The tanpura employs a traditional 4-string cycle:
      - String 1: Pa (G#3 = 207.6523 Hz)
      - String 2: Jod Sa (C#4 = 277.1826 Hz)
      - String 3: Jod Sa (C#4 = 277.1826 Hz, micro-detuned +0.4 Hz for shimmer)
      - String 4: Kharaj Sa (C#3 = 138.5913 Hz)

    Each pluck simulates jawari (bridge grazing) with rich non-linear harmonic series
    and natural exponential resonance decay.
    """
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)

    left_channel = np.zeros(total_samples, dtype=np.float64)
    right_channel = np.zeros(total_samples, dtype=np.float64)

    # 4 strings configuration: (freq_hz, pan [-1..+1], decay_rate, base_amp)
    strings = [
        {"freq": DOMINANT_GSHARP3_HZ, "pan": -0.25, "decay": 0.45, "amp": 0.70},  # Pa (G#3)
        {"freq": OCTAVE_CSHARP4_HZ, "pan": -0.08, "decay": 0.50, "amp": 0.65},    # Jod Sa 1 (C#4)
        {"freq": OCTAVE_CSHARP4_HZ * 1.0015, "pan": 0.08, "decay": 0.50, "amp": 0.65},  # Jod Sa 2 (shimmer)
        {"freq": TONIC_CSHARP3_HZ, "pan": 0.25, "decay": 0.35, "amp": 0.85},     # Kharaj Sa (C#3)
    ]

    cycle_period = 5.0  # seconds per 4-string cycle (1.25s per string)
    string_interval = 1.25

    # Render plucks across the entire duration plus lead-out
    current_time = 0.0
    while current_time < duration_sec:
        for idx, string in enumerate(strings):
            pluck_time = current_time + idx * string_interval
            if pluck_time >= duration_sec + 2.0:
                break

            pluck_sample = int(pluck_time * sr)
            decay_sec = 6.5
            decay_samples = min(int(decay_sec * sr), total_samples - pluck_sample)
            if decay_samples <= 0:
                continue

            t_decay = np.linspace(0, decay_sec, decay_samples, endpoint=False)
            f0 = string["freq"]

            # Jawari harmonics: 1 through 20 with non-linear overtone envelope
            harmonics_signal = np.zeros(decay_samples, dtype=np.float64)
            for h in range(1, 21):
                h_freq = f0 * h
                if h_freq >= sr / 2:
                    break
                # Jawari accentuates harmonics 3 to 9 with subtle slow amplitude modulation
                mod_freq = 1.2 + 0.3 * (h % 3)
                jawari_mod = 1.0 + 0.25 * np.sin(2 * np.pi * mod_freq * t_decay)
                # Harmonic weight
                h_weight = (1.0 / (h ** 0.85)) * jawari_mod
                phase = np.random.uniform(0, 2 * np.pi)
                harmonics_signal += h_weight * np.sin(2 * np.pi * h_freq * t_decay + phase)

            # Pluck envelope: rapid 15ms attack + exponential decay
            attack_samples = int(0.015 * sr)
            attack = np.linspace(0.0, 1.0, min(attack_samples, decay_samples))
            envelope = np.exp(-string["decay"] * t_decay)
            envelope[:len(attack)] *= attack

            string_signal = harmonics_signal * envelope * string["amp"]

            # Panning (constant power)
            pan = string["pan"]  # -1..+1
            angle = (pan + 1.0) * (np.pi / 4.0)  # 0 to pi/2
            gain_l = np.cos(angle)
            gain_r = np.sin(angle)

            end_sample = pluck_sample + decay_samples
            if pluck_sample < total_samples:
                avail = min(decay_samples, total_samples - pluck_sample)
                left_channel[pluck_sample : pluck_sample + avail] += string_signal[:avail] * gain_l
                right_channel[pluck_sample : pluck_sample + avail] += string_signal[:avail] * gain_r

        current_time += cycle_period

    # Continuous background resonance hum (Sa + Pa fundamentals)
    resonance_l = 0.08 * np.sin(2 * np.pi * TONIC_CSHARP3_HZ * t) + 0.04 * np.sin(2 * np.pi * DOMINANT_GSHARP3_HZ * t)
    resonance_r = 0.08 * np.sin(2 * np.pi * TONIC_CSHARP3_HZ * t + 0.5) + 0.04 * np.sin(2 * np.pi * DOMINANT_GSHARP3_HZ * t - 0.5)
    left_channel += resonance_l
    right_channel += resonance_r

    # Make phase-continuous & loop-ready: smooth 0.5s cosine crossfade at head and tail
    fade_len = int(0.5 * sr)
    fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_len)))
    fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len)))
    left_channel[:fade_len] *= fade_in
    right_channel[:fade_len] *= fade_in
    left_channel[-fade_len:] *= fade_out
    right_channel[-fade_len:] *= fade_out

    # Normalize to -3 dBFS peak
    stereo = np.stack([left_channel, right_channel], axis=-1)
    max_peak = np.max(np.abs(stereo))
    if max_peak > 0:
        target_peak = 10.0 ** (-3.0 / 20.0)  # ~0.707
        stereo = stereo * (target_peak / max_peak)

    return stereo.astype(np.float32)


def synthesize_mandapa_impulse_response(
    rt60_sec: float = 1.35,
    duration_sec: float = 2.5,
    sr: int = SAMPLE_RATE_MASTER,
) -> np.ndarray:
    """Synthesizes a stereo stone maṇḍapa impulse response with RT60 = 1.35s.

    Stone temple mandapas exhibit:
      - Distinct early reflections from stone pillars and granite slabs
      - Dense late reverberation with exponential decay (RT60 = 1.35s)
      - Slight high-frequency absorption roll-off simulating air/stone damping
    """
    total_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)

    # Decay constant for RT60 (60 dB attenuation = factor of 10^-3)
    tau = rt60_sec / (math.log(1000.0))  # approx 1.35 / 6.90775 ~ 0.1954s
    decay_envelope = np.exp(-t / tau)

    # 1. Early Reflections (simulating granite pillar delays)
    early_delays_ms = [8, 17, 26, 39, 53, 67, 85, 104, 128]
    ir_l = np.zeros(total_samples, dtype=np.float64)
    ir_r = np.zeros(total_samples, dtype=np.float64)

    # Direct sound impulse at t=0
    ir_l[0] = 1.0
    ir_r[0] = 1.0

    np.random.seed(42)
    for d_ms in early_delays_ms:
        sample_l = int((d_ms / 1000.0) * sr)
        sample_r = int(((d_ms + np.random.uniform(-1.5, 1.5)) / 1000.0) * sr)
        amp_l = np.exp(-(d_ms / 1000.0) / tau) * np.random.uniform(0.3, 0.6) * (1 if np.random.rand() > 0.3 else -1)
        amp_r = np.exp(-(d_ms / 1000.0) / tau) * np.random.uniform(0.3, 0.6) * (1 if np.random.rand() > 0.3 else -1)
        if sample_l < total_samples:
            ir_l[sample_l] += amp_l
        if sample_r < total_samples:
            ir_r[sample_r] += amp_r

    # 2. Diffuse Late Reverberant Tail (decorrelated stereo Gaussian noise)
    noise_l = np.random.normal(0.0, 1.0, total_samples)
    noise_r = np.random.normal(0.0, 1.0, total_samples)

    # Soft low-pass damping on diffuse noise to simulate high-frequency air/granite loss
    # Simple recursive 1-pole filter: y[n] = (1 - a)*x[n] + a*y[n-1]
    alpha = 0.35
    for n in range(1, total_samples):
        noise_l[n] = (1 - alpha) * noise_l[n] + alpha * noise_l[n - 1]
        noise_r[n] = (1 - alpha) * noise_r[n] + alpha * noise_r[n - 1]

    # Diffuse onset ramps up over 25ms to avoid unnatural pre-delay burst
    diffuse_onset = np.minimum(1.0, t / 0.025)
    diffuse_weight = 0.45

    ir_l += noise_l * decay_envelope * diffuse_onset * diffuse_weight
    ir_r += noise_r * decay_envelope * diffuse_onset * diffuse_weight

    # Peak normalization to -1 dBFS
    stereo_ir = np.stack([ir_l, ir_r], axis=-1)
    max_peak = np.max(np.abs(stereo_ir))
    if max_peak > 0:
        target_peak = 10.0 ** (-1.0 / 20.0)  # ~0.891
        stereo_ir = stereo_ir * (target_peak / max_peak)

    return stereo_ir.astype(np.float32)


def generate_all_acoustics() -> None:
    """Generates both reference acoustic files into storage/acoustics/."""
    ACOUSTICS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating 60s C#3 Tanpura drone ({TONIC_CSHARP3_HZ:.4f} Hz) -> {TANPURA_WAV_PATH}...")
    tanpura_audio = synthesize_tanpura_drone(duration_sec=60.0, sr=SAMPLE_RATE_MASTER)
    sf.write(str(TANPURA_WAV_PATH), tanpura_audio, SAMPLE_RATE_MASTER, subtype="PCM_24")
    print(f"Tanpura saved successfully. Shape: {tanpura_audio.shape}, Sample Rate: {SAMPLE_RATE_MASTER} Hz.")

    print(f"Generating stone mandapa impulse response (RT60 = 1.35s) -> {MANDAPA_IR_PATH}...")
    ir_audio = synthesize_mandapa_impulse_response(rt60_sec=1.35, duration_sec=2.5, sr=SAMPLE_RATE_MASTER)
    sf.write(str(MANDAPA_IR_PATH), ir_audio, SAMPLE_RATE_MASTER, subtype="PCM_24")
    print(f"Impulse response saved successfully. Shape: {ir_audio.shape}, Sample Rate: {SAMPLE_RATE_MASTER} Hz.")


if __name__ == "__main__":
    generate_all_acoustics()
