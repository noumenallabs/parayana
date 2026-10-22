"use client";

import React, { useEffect, useState } from "react";
import VoiceForgeLab from "@/components/VoiceForgeLab";
import { Persona, listPersonas } from "@/lib/api";
import { Mic, ShieldCheck } from "lucide-react";

export default function AdminVoicesPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listPersonas();
        setPersonas(data);
      } catch (err) {
        console.error("Failed to load personas", err);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const handleCreated = (newP: Persona) => {
    setPersonas((prev) => [...prev, newP]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-mandapa-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Mic className="w-5 h-5 text-mandapa-gold" />
            <span>Admin Pandit Persona Forge & Timbre Lab</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Curate proprietary Indian vocal timbres, sculpt formants, and blend CAMPPlus 192-D speaker embeddings
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
          <ShieldCheck className="w-4 h-4" />
          <span>F0 Locked to 138.59 Hz (C#3)</span>
        </div>
      </div>

      {!isLoading && (
        <VoiceForgeLab initialPersonas={personas} onPersonaCreated={handleCreated} />
      )}
    </div>
  );
}
