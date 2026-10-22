"use client";

import React, { useState } from "react";
import { Mic, Sliders, Layers, Sparkles, Volume2, CheckCircle2, RefreshCw } from "lucide-react";
import { Persona, blendPersonas, forgePersona } from "@/lib/api";

interface VoiceForgeLabProps {
  initialPersonas: Persona[];
  onPersonaCreated: (newPersona: Persona) => void;
}

export default function VoiceForgeLab({ initialPersonas, onPersonaCreated }: VoiceForgeLabProps) {
  const [activeTab, setActiveTab] = useState<"forge" | "blend">("forge");
  const [personas, setPersonas] = useState<Persona[]>(initialPersonas);

  // Tab 1: Forge Form State
  const [name, setName] = useState("Śrī Nārada (Celestial Tenor)");
  const [roleTag, setRoleTag] = useState("Bright Tenor");
  const [prompt, setPrompt] = useState(
    "A resonant Indian Vedic reciter chanting in high tenor with devotional clarity and gentle vibrato"
  );
  const [formantShift, setFormantShift] = useState(0.8);
  const [chestDb, setChestDb] = useState(-0.5);
  const [presenceDb, setPresenceDb] = useState(2.0);
  const [airDb, setAirDb] = useState(1.5);
  const [isForging, setIsForging] = useState(false);

  // Tab 2: Blend Form State
  const [blendName, setBlendName] = useState("Śrī Madhva-Rāghava (Blended)");
  const [parentAId, setParentAId] = useState(initialPersonas[0]?.id || "pandit_1_mukhya");
  const [parentBId, setParentBId] = useState(initialPersonas[1]?.id || "pandit_2_vriddha");
  const [blendAlpha, setBlendAlpha] = useState(0.5);
  const [isBlending, setIsBlending] = useState(false);

  const handleForge = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsForging(true);
    try {
      const p = await forgePersona({
        name,
        role_tag: roleTag,
        prompt,
        formant_shift_st: formantShift,
        chest_db: chestDb,
        presence_db: presenceDb,
        air_db: airDb,
        default_pan: 0.0,
        default_gain_db: 0.0,
      });
      setPersonas((prev) => [...prev, p]);
      onPersonaCreated(p);
      alert(`Persona '${p.name}' forged and saved successfully!`);
    } catch (err: any) {
      alert(`Forge failed: ${err.message}`);
    } finally {
      setIsForging(false);
    }
  };

  const handleBlend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (parentAId === parentBId) {
      alert("Please select two distinct parent personas to blend.");
      return;
    }
    setIsBlending(true);
    try {
      const p = await blendPersonas({
        name: blendName,
        role_tag: "Blended Voice",
        parent_a_id: parentAId,
        parent_b_id: parentBId,
        alpha: blendAlpha,
        default_pan: 0.0,
        default_gain_db: 0.0,
      });
      setPersonas((prev) => [...prev, p]);
      onPersonaCreated(p);
      alert(`Blended Persona '${p.name}' created via slerp interpolation!`);
    } catch (err: any) {
      alert(`Blend failed: ${err.message}`);
    } finally {
      setIsBlending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-mandapa-800 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("forge")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeTab === "forge"
              ? "bg-amber-500/20 text-mandapa-gold border border-mandapa-gold/30 shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Mic className="w-4 h-4" />
          <span>Tab 1: Text-to-Persona Designer</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("blend")}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeTab === "blend"
              ? "bg-amber-500/20 text-mandapa-gold border border-mandapa-gold/30 shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Tab 2: CAMPPlus 192-D Embedding Blender</span>
        </button>
      </div>

      {/* Tab 1: Text-to-Persona Designer */}
      {activeTab === "forge" && (
        <form onSubmit={handleForge} className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-6 shadow-xl space-y-6">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-mandapa-gold" />
              <span>Synthesize & Sculpt New Pandit Persona</span>
            </h3>
            <p className="text-xs text-slate-400">
              Generates proprietary Indian male vocal timbres with sustained-vowel calibration (C#3 138.59 Hz)
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Persona Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Ensemble Role Tag</label>
              <select
                value={roleTag}
                onChange={(e) => setRoleTag(e.target.value)}
                className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              >
                <option value="Lead Center">Lead Center (Mukhya)</option>
                <option value="Deep Elder">Deep Elder (Vṛddha)</option>
                <option value="Bass-Baritone">Bass-Baritone (Ghanapāṭhī)</option>
                <option value="Bright Tenor">Bright Tenor (Yuva)</option>
                <option value="Warm Support">Warm Support (Upagāyaka)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Parler-TTS Persona Description Prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-3 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              placeholder="Describe vocal timbre, age, resonance..."
              required
            />
          </div>

          {/* Formant & 3-Band EQ Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-lg bg-mandapa-950/60 border border-mandapa-800">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300">Vocal-Tract Formant</span>
                <span className="font-mono text-mandapa-gold">{formantShift.toFixed(1)} st</span>
              </div>
              <input
                type="range"
                min={-2.5}
                max={2.5}
                step={0.1}
                value={formantShift}
                onChange={(e) => setFormantShift(Number(e.target.value))}
                className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
              />
              <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                <span>Larger (-2.5)</span>
                <span>Smaller (+2.5)</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300">160 Hz Chest EQ</span>
                <span className="font-mono text-mandapa-gold">{chestDb.toFixed(1)} dB</span>
              </div>
              <input
                type="range"
                min={-6}
                max={6}
                step={0.5}
                value={chestDb}
                onChange={(e) => setChestDb(Number(e.target.value))}
                className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300">1.8 kHz Presence</span>
                <span className="font-mono text-mandapa-gold">{presenceDb.toFixed(1)} dB</span>
              </div>
              <input
                type="range"
                min={-6}
                max={6}
                step={0.5}
                value={presenceDb}
                onChange={(e) => setPresenceDb(Number(e.target.value))}
                className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300">4.5 kHz Air EQ</span>
                <span className="font-mono text-mandapa-gold">{airDb.toFixed(1)} dB</span>
              </div>
              <input
                type="range"
                min={-6}
                max={6}
                step={0.5}
                value={airDb}
                onChange={(e) => setAirDb(Number(e.target.value))}
                className="w-full accent-mandapa-gold h-1.5 bg-mandapa-800 rounded cursor-pointer"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isForging}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-slate-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all"
            >
              {isForging ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Persona...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 fill-slate-950" />
                  <span>Synthesize & Save Persona</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Tab 2: CAMPPlus 192-D Embedding Blender */}
      {activeTab === "blend" && (
        <form onSubmit={handleBlend} className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-6 shadow-xl space-y-6">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-mandapa-gold" />
              <span>Spherical Linear Interpolation (slerp) Voice Blender</span>
            </h3>
            <p className="text-xs text-slate-400">
              Blends two CAMPPlus 192-D speaker representations while preserving vector norm and unison C#3 pitch
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Blended Persona Name</label>
            <input
              type="text"
              value={blendName}
              onChange={(e) => setBlendName(e.target.value)}
              className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Parent Voice A</label>
              <select
                value={parentAId}
                onChange={(e) => setParentAId(e.target.value)}
                className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              >
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.role_tag})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Parent Voice B</label>
              <select
                value={parentBId}
                onChange={(e) => setParentBId(e.target.value)}
                className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-2.5 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              >
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.role_tag})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Slerp Blend Ratio Slider */}
          <div className="p-4 rounded-lg bg-mandapa-950/60 border border-mandapa-800 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-300 font-medium">Blend Ratio (alpha: {blendAlpha.toFixed(2)})</span>
              <span className="font-mono text-mandapa-gold">
                {((1 - blendAlpha) * 100).toFixed(0)}% Parent A / {(blendAlpha * 100).toFixed(0)}% Parent B
              </span>
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.05}
              value={blendAlpha}
              onChange={(e) => setBlendAlpha(Number(e.target.value))}
              className="w-full accent-mandapa-gold h-2 bg-mandapa-800 rounded cursor-pointer"
            />
            <div className="text-[11px] text-slate-400 flex justify-between">
              <span>100% Parent A</span>
              <span>Balanced 50/50</span>
              <span>100% Parent B</span>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isBlending}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-slate-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all"
            >
              {isBlending ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Computing Slerp Blend...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 fill-slate-950" />
                  <span>Save Blended Persona</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Available Virtual Pandits Library */}
      <div className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-mandapa-gold" />
          <span>Active Virtual Pandit Ensemble ({personas.length} Personas)</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {personas.map((p) => (
            <div
              key={p.id}
              className="p-3.5 rounded-lg bg-mandapa-950 border border-mandapa-800 flex items-center justify-between"
            >
              <div>
                <div className="font-semibold text-white text-xs">{p.name}</div>
                <div className="text-[11px] text-slate-400">{p.role_tag}</div>
                <div className="text-[10px] font-mono text-amber-400/80 mt-0.5">
                  pan: {p.default_pan >= 0 ? `+${p.default_pan}` : p.default_pan} • {p.creation_mode}
                </div>
              </div>
              <div className="w-8 h-8 rounded-full bg-mandapa-800 flex items-center justify-center text-mandapa-gold">
                <Mic className="w-4 h-4" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
