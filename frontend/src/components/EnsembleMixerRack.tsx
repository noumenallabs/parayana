"use client";

import React, { useState } from "react";
import { Play, Pause, Sliders, Volume2, Mic, Zap, Sparkles } from "lucide-react";

interface EnsembleMixerRackProps {
  renderMode: "preview_dsp" | "studio_seedvc";
  onRenderModeChange: (mode: "preview_dsp" | "studio_seedvc") => void;
  chantSpeed: number;
  onChantSpeedChange: (speed: number) => void;
  tanpuraGainDb: number;
  onTanpuraGainChange: (gain: number) => void;
  reverbWet: number;
  onReverbWetChange: (wet: number) => void;
  interVersePauseSec: number;
  onInterVersePauseChange: (pause: number) => void;
  isRendering: boolean;
  onStartRender: () => void;
  onPauseRender: () => void;
}

const DEFAULT_PANDITS = [
  { id: "pandit_4_yuva", name: "Śrī Yuva", tag: "Bright Tenor", angle: "-45°", pan: -0.45 },
  { id: "pandit_2_vriddha", name: "Śrī Vṛddha", tag: "Deep Elder", angle: "-22°", pan: -0.22 },
  { id: "pandit_1_mukhya", name: "Śrī Mukhya", tag: "Lead Center", angle: "0°", pan: 0.0, isLead: true },
  { id: "pandit_3_ghanapathi", name: "Śrī Ghanapāṭhī", tag: "Bass-Baritone", angle: "+22°", pan: 0.22 },
  { id: "pandit_5_upagayaka", name: "Śrī Upagāyaka", tag: "Warm Support", angle: "+45°", pan: 0.45 },
];

export default function EnsembleMixerRack({
  renderMode,
  onRenderModeChange,
  chantSpeed,
  onChantSpeedChange,
  tanpuraGainDb,
  onTanpuraGainChange,
  reverbWet,
  onReverbWetChange,
  interVersePauseSec,
  onInterVersePauseChange,
  isRendering,
  onStartRender,
  onPauseRender,
}: EnsembleMixerRackProps) {
  const [muted, setMuted] = useState<{ [id: string]: boolean }>({});

  const toggleMute = (id: string) => {
    setMuted((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-5 shadow-lg space-y-6">
      {/* Header & Mode Switch */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-mandapa-800 pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-mandapa-gold" />
            <span>5-Pandit Semicircle Stage & Acoustic Bus</span>
          </h2>
          <p className="text-xs text-slate-400">
            Phase-locked unison chanting anchored to C#3 (138.59 Hz) ādhāra-ṣaḍja
          </p>
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center gap-2 bg-mandapa-950 p-1.5 rounded-lg border border-mandapa-700">
          <button
            type="button"
            onClick={() => onRenderModeChange("preview_dsp")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all ${
              renderMode === "preview_dsp"
                ? "bg-amber-500/20 text-mandapa-gold border border-mandapa-gold/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>⚡ Fast Preview (DSP)</span>
          </button>
          <button
            type="button"
            onClick={() => onRenderModeChange("studio_seedvc")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all ${
              renderMode === "studio_seedvc"
                ? "bg-amber-500/20 text-mandapa-gold border border-mandapa-gold/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>🎙️ Studio Master (Seed-VC)</span>
          </button>
        </div>
      </div>

      {/* Semicircle Spatial Stage */}
      <div className="relative bg-mandapa-950/60 border border-mandapa-800/80 rounded-xl p-6 overflow-hidden">
        <div className="text-center text-[11px] font-mono text-slate-400 tracking-wider mb-2">
          TEMPLE MAṆḌAPA STEREO SOUNDSTAGE (48 kHz)
        </div>

        {/* Semicircle Arch visual */}
        <div className="relative h-28 max-w-lg mx-auto flex items-end justify-between px-4 pb-2">
          {/* Subtle curved background guideline */}
          <div className="absolute inset-x-8 top-4 bottom-2 border-t-2 border-dashed border-mandapa-700/40 rounded-t-full pointer-events-none" />

          {DEFAULT_PANDITS.map((p) => {
            const isMute = !!muted[p.id];
            return (
              <div
                key={p.id}
                className="flex flex-col items-center gap-1.5 z-10"
              >
                <button
                  type="button"
                  onClick={() => toggleMute(p.id)}
                  title={`${p.name} (${p.angle}) - Click to mute`}
                  className={`w-12 h-12 rounded-full border flex flex-col items-center justify-center transition-all ${
                    isMute
                      ? "bg-mandapa-800 border-mandapa-700 opacity-40"
                      : p.isLead
                      ? "bg-amber-500 text-slate-950 border-amber-400 shadow-lg shadow-amber-500/30 scale-110"
                      : "bg-mandapa-800 text-slate-200 border-mandapa-700 hover:border-mandapa-gold/50"
                  }`}
                >
                  <Mic className="w-4 h-4" />
                  <span className="text-[9px] font-mono font-bold leading-none mt-0.5">
                    {p.angle}
                  </span>
                </button>
                <span className="text-[11px] font-medium text-slate-200 text-center">
                  {p.name.replace("Śrī ", "")}
                </span>
                <span className="text-[10px] text-slate-400">{p.tag}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Controls & Acoustic Sliders */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tanpura Drone */}
        <div className="bg-mandapa-950/70 border border-mandapa-800 rounded-lg p-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-300 font-medium">C#3 Tanpura Bed</span>
            <span className="font-mono text-mandapa-gold">{tanpuraGainDb.toFixed(1)} dB</span>
          </div>
          <input
            type="range"
            min={-36}
            max={-6}
            step={0.5}
            value={tanpuraGainDb}
            onChange={(e) => onTanpuraGainChange(Number(e.target.value))}
            className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
          />
          <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
            <span>Subtle</span>
            <span>Prominent</span>
          </div>
        </div>

        {/* Mandapa Reverb */}
        <div className="bg-mandapa-950/70 border border-mandapa-800 rounded-lg p-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-300 font-medium">Stone Maṇḍapa Reverb</span>
            <span className="font-mono text-mandapa-gold">{(reverbWet * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min={0.0}
            max={0.45}
            step={0.01}
            value={reverbWet}
            onChange={(e) => onReverbWetChange(Number(e.target.value))}
            className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
          />
          <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
            <span>Direct</span>
            <span>RT60 1.35s</span>
          </div>
        </div>

        {/* Chant Speed */}
        <div className="bg-mandapa-950/70 border border-mandapa-800 rounded-lg p-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-300 font-medium">Chanting Pace</span>
            <span className="font-mono text-mandapa-gold">{chantSpeed.toFixed(2)}×</span>
          </div>
          <input
            type="range"
            min={0.75}
            max={1.25}
            step={0.05}
            value={chantSpeed}
            onChange={(e) => onChantSpeedChange(Number(e.target.value))}
            className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
          />
          <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
            <span>Druta (Fast)</span>
            <span>Vilambita (Slow)</span>
          </div>
        </div>

        {/* Inter-Verse Pause */}
        <div className="bg-mandapa-950/70 border border-mandapa-800 rounded-lg p-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-300 font-medium">Inter-Verse Pause</span>
            <span className="font-mono text-mandapa-gold">{interVersePauseSec.toFixed(2)}s</span>
          </div>
          <input
            type="range"
            min={0.4}
            max={2.5}
            step={0.05}
            value={interVersePauseSec}
            onChange={(e) => onInterVersePauseChange(Number(e.target.value))}
            className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
          />
          <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
            <span>Breath (0.4s)</span>
            <span>Pause (2.5s)</span>
          </div>
        </div>
      </div>

      {/* Render Action Buttons */}
      <div className="flex items-center justify-between border-t border-mandapa-800 pt-4">
        <div className="text-xs text-slate-400">
          Mode: <strong className="text-slate-200">{renderMode === "studio_seedvc" ? "Neural Seed-VC Master" : "Fast Preview (DSP)"}</strong>
        </div>

        <div className="flex items-center gap-3">
          {isRendering ? (
            <button
              type="button"
              onClick={onPauseRender}
              className="px-5 py-2.5 rounded-lg bg-mandapa-800 hover:bg-mandapa-700 text-amber-300 font-medium text-sm flex items-center gap-2 border border-mandapa-700"
            >
              <Pause className="w-4 h-4" />
              <span>Pause Chanting</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onStartRender}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-slate-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-amber-500/20"
            >
              <Play className="w-4 h-4 fill-slate-950" />
              <span>Render All Verses</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
