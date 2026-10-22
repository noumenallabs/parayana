"use client";

import React, { useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  Play,
  Pause,
  RotateCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Music,
} from "lucide-react";
import { Verse } from "@/lib/api";

interface VerseQueueTableProps {
  verses: Verse[];
  onRerollVerse: (verseIndex: number) => void;
  onUpdateMeter: (verseIndex: number, meter: string) => void;
  rerollingIndex: number | null;
}

const CLASSICAL_METERS = [
  "anushtubh",
  "vasantatilaka",
  "indravajra",
  "upendravajra",
  "upajati",
  "vamshastha",
  "indravamsha",
  "malini",
  "mandakranta",
  "shikharini",
  "harini",
  "prithvi",
  "shardulavikridita",
  "sragdhara",
  "pramanika",
  "gayatri",
  "gadya",
];

export default function VerseQueueTable({
  verses,
  onRerollVerse,
  onUpdateMeter,
  rerollingIndex,
}: VerseQueueTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [expandedKannada, setExpandedKannada] = useState<{ [idx: number]: boolean }>({});
  const [playingVerseIndex, setPlayingVerseIndex] = useState<number | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  const rowVirtualizer = useVirtualizer({
    count: verses.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 110,
    overscan: 5,
  });

  const toggleKannada = (idx: number) => {
    setExpandedKannada((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handlePlayAudio = (v: Verse) => {
    if (!v.mixed_verse_wav_path) return;

    if (playingVerseIndex === v.verse_index && audioElement) {
      audioElement.pause();
      setPlayingVerseIndex(null);
      return;
    }

    if (audioElement) {
      audioElement.pause();
    }

    const relPath = v.mixed_verse_wav_path.replace(/\\/g, "/");
    // Ensure relative audio URL
    const audioUrl = `/audio/projects/${v.project_id}/v${v.verse_index.toString().padStart(3, "0")}_mixed.wav`;
    const audio = new Audio(audioUrl);
    audio.play();
    audio.onended = () => setPlayingVerseIndex(null);
    setAudioElement(audio);
    setPlayingVerseIndex(v.verse_index);
  };

  const getQCBadge = (status: string) => {
    switch (status) {
      case "PASS":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            <span>PASS</span>
          </span>
        );
      case "SILENCE_FLAG":
      case "DURATION_FLAG":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3 h-3" />
            <span>{status.replace("_FLAG", "")}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Clock className="w-3 h-3" />
            <span>PENDING</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-mandapa-900 border border-mandapa-800 rounded-xl overflow-hidden shadow-lg flex flex-col">
      <div className="px-5 py-3.5 border-b border-mandapa-800 flex items-center justify-between bg-mandapa-950/40">
        <div>
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <Music className="w-4 h-4 text-mandapa-gold" />
            <span>Verse Queue & Guru/Laghu Prosody Scansion</span>
          </h2>
          <p className="text-xs text-slate-400">
            {verses.length} verses • Virtualized window for 150+ Sahasranāma recitation
          </p>
        </div>
      </div>

      {/* Virtualized Container */}
      <div
        ref={parentRef}
        className="h-[460px] overflow-y-auto w-full divide-y divide-mandapa-800"
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: "100%",
            position: "relative",
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const verse = verses[virtualRow.index];
            const isExpanded = !!expandedKannada[verse.verse_index];
            const isPlaying = playingVerseIndex === verse.verse_index;
            const isRerolling = rerollingIndex === verse.verse_index;

            return (
              <div
                key={verse.id || virtualRow.index}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className="p-4 hover:bg-mandapa-950/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                {/* Left: Verse Index, Section, Texts */}
                <div className="flex-1 space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap text-xs">
                    <span className="font-mono font-bold text-mandapa-gold">
                      #{verse.verse_index.toString().padStart(3, "0")}
                    </span>

                    <span className="px-2 py-0.5 rounded bg-mandapa-800 text-slate-300 text-[10px] font-semibold">
                      {verse.section_label}
                    </span>

                    {verse.unit_type !== "METRICAL_SLOKA" && (
                      <span className="px-2 py-0.5 rounded bg-amber-900/40 text-amber-300 border border-amber-700/40 text-[10px] font-mono">
                        {verse.unit_type}
                      </span>
                    )}

                    {getQCBadge(verse.qc_status)}

                    {verse.syllable_count > 0 && (
                      <span className="text-[11px] font-mono text-slate-400">
                        {verse.syllable_count} akṣaras
                      </span>
                    )}

                    {verse.lg_signature && (
                      <span
                        className="text-[11px] font-mono text-amber-400/80 bg-mandapa-950 px-1.5 py-0.5 rounded border border-mandapa-800 truncate max-w-[200px]"
                        title={verse.lg_signature}
                      >
                        {verse.lg_signature}
                      </span>
                    )}
                  </div>

                  {/* Devanagari Sanskrit Text */}
                  <div className="text-sm font-medium text-slate-100 whitespace-pre-line leading-relaxed font-serif">
                    {verse.raw_text}
                  </div>

                  {/* Collapsible Kannada Routing */}
                  <div>
                    <button
                      type="button"
                      onClick={() => toggleKannada(verse.verse_index)}
                      className="text-[11px] text-slate-400 hover:text-mandapa-gold flex items-center gap-1 transition-colors"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      <span>Kannada Phonetic Routing</span>
                    </button>
                    {isExpanded && (
                      <div className="text-xs text-amber-300/80 font-mono mt-1 p-2 rounded bg-mandapa-950 border border-mandapa-800">
                        {verse.kannada_text}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right: Meter Override, Inline Audio, Re-roll */}
                <div className="flex items-center gap-3 shrink-0">
                  {/* Meter Dropdown */}
                  <div className="flex flex-col text-[10px]">
                    <span className="text-slate-400 mb-0.5">Meter Override</span>
                    <select
                      value={verse.override_meter || verse.detected_meter || "anushtubh"}
                      onChange={(e) => onUpdateMeter(verse.verse_index, e.target.value)}
                      className="bg-mandapa-950 border border-mandapa-700 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-mandapa-gold"
                    >
                      {CLASSICAL_METERS.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Inline Audio Player */}
                  {verse.mixed_verse_wav_path && (
                    <button
                      type="button"
                      onClick={() => handlePlayAudio(verse)}
                      className={`p-2 rounded-full border transition-all ${
                        isPlaying
                          ? "bg-mandapa-gold text-slate-950 border-amber-400 shadow-md"
                          : "bg-mandapa-800 text-slate-300 border-mandapa-700 hover:border-mandapa-gold"
                      }`}
                      title={isPlaying ? "Pause" : "Play verse audio"}
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                    </button>
                  )}

                  {/* Single-Verse Re-roll (↻) */}
                  <button
                    type="button"
                    onClick={() => onRerollVerse(verse.verse_index)}
                    disabled={isRerolling}
                    className="p-2 rounded-lg bg-mandapa-800 hover:bg-mandapa-700 text-slate-300 hover:text-mandapa-gold border border-mandapa-700 disabled:opacity-50 transition-colors"
                    title={`Re-roll stochastic seed (seed: ${verse.base_seed})`}
                  >
                    <RotateCw className={`w-4 h-4 ${isRerolling ? "animate-spin text-mandapa-gold" : ""}`} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
