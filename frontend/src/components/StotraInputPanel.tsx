"use client";

import React, { useState } from "react";
import { BookOpen, Sparkles, RefreshCw } from "lucide-react";

interface StotraInputPanelProps {
  onProjectCreated: (project: any) => void;
  isLoading: boolean;
}

const SAMPLE_STOTRAS = [
  {
    name: "Śrī Kṛṣṇa Mangala Śloka",
    text: `पूर्वपीठिका
शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।
प्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥

स्तोत्रम्
वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।
देवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥`,
  },
  {
    name: "Śrī Madhvācārya Mangalācaraṇam (Vasantatilakā)",
    text: `स्तोत्रम्
नारायणाय परिपूर्णगुणार्णवाय विश्वोदयस्थितिलयोन्नियतिप्रदाय ।
ज्ञानप्रदाय विबुधासुरसौख्यदुःखसत्कारणाय वितताय नमो नमस्ते ॥`,
  },
];

export default function StotraInputPanel({ onProjectCreated, isLoading }: StotraInputPanelProps) {
  const [title, setTitle] = useState("Śrī Viṣṇu Stotram");
  const [rawText, setRawText] = useState(SAMPLE_STOTRAS[0].text);
  const [japaMode, setJapaMode] = useState<number | "none">("none");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    try {
      const payload: any = {
        title,
        raw_input_text: rawText,
        japa_repeat_count: japaMode === "none" ? null : Number(japaMode),
      };
      onProjectCreated(payload);
    } catch (err: any) {
      alert(`Error submitting stotra: ${err.message}`);
    }
  };

  return (
    <div className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-mandapa-800 pb-3">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-mandapa-gold" />
          <h2 className="text-base font-semibold text-white">Sanskrit Text & Liturgical Parser</h2>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Load sample:</span>
          {SAMPLE_STOTRAS.map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setTitle(s.name);
                setRawText(s.text);
              }}
              className="px-2.5 py-1 rounded bg-mandapa-800 hover:bg-mandapa-700 text-slate-300 transition-colors"
            >
              {s.name.split(" ")[1] || "Sample"}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Composition / Stotra Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
              placeholder="e.g. Śrī Viṣṇu Sahasranāma Stotram"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Chant Mode
            </label>
            <select
              value={String(japaMode)}
              onChange={(e) => setJapaMode(e.target.value === "none" ? "none" : Number(e.target.value))}
              className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-mandapa-gold"
            >
              <option value="none">Sahasranāma / Metrical Stotra</option>
              <option value="11">Japa 11× (3 units × 4 reps)</option>
              <option value="21">Japa 21× (6 units × 4 reps)</option>
              <option value="54">Japa 54× (14 units × 4 reps)</option>
              <option value="108">Japa 108× (27 units × 4 reps)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center justify-between">
            <span>Sanskrit Input (Devanagari, Kannada, Telugu, Grantha, etc.)</span>
            <span className="text-slate-400">Vedic accents & verse numbers automatically normalized</span>
          </label>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={5}
            className="w-full bg-mandapa-950 border border-mandapa-700 rounded-lg p-3 text-sm text-slate-100 font-mono focus:outline-none focus:border-mandapa-gold leading-relaxed"
            placeholder="Paste complete Stotra, Sahasranāma, or Mantra..."
            required
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-slate-400">
            Accepts complete Sahasranāma texts (108–160+ verses). Segmented into discrete VerseUnits.
          </p>
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-slate-950 font-semibold text-sm flex items-center gap-2 shadow-md shadow-amber-500/20 disabled:opacity-50 transition-all"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Scanning & Segmenting...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 fill-slate-950" />
                <span>Scan & Segment Verses</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
