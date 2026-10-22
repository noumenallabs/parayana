import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Mic, Music, Sliders, Shield } from "lucide-react";

export const metadata: Metadata = {
  title: "Vāgdhenu Goṣṭhī Studio — Multi-Pandit Chanting Suite",
  description: "Neural Vocal Ensemble & Sahasranāma Mastering Suite anchored to C#3 Unison Tonic",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-mandapa-950 text-slate-100 min-h-screen flex flex-col">
        <header className="border-b border-mandapa-800 bg-mandapa-900/90 backdrop-blur sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-amber-600 via-amber-500 to-yellow-400 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Music className="w-5 h-5 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <div className="font-bold tracking-tight text-white flex items-center gap-2">
                <span>Vāgdhenu Goṣṭhī Studio</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-mandapa-gold/20 text-mandapa-gold border border-mandapa-gold/30">
                  v2.1 Master
                </span>
              </div>
              <p className="text-xs text-slate-400">
                138.59 Hz (C#3) Unison Tonic • 48 kHz / 24-bit Mastering
              </p>
            </div>
          </div>

          <nav className="flex items-center gap-2 text-sm font-medium">
            <Link
              href="/"
              className="px-3.5 py-1.5 rounded-lg hover:bg-mandapa-800 text-slate-200 transition-colors flex items-center gap-2"
            >
              <Sliders className="w-4 h-4 text-mandapa-gold" />
              <span>Stotra Studio</span>
            </Link>
            <Link
              href="/admin/voices"
              className="px-3.5 py-1.5 rounded-lg hover:bg-mandapa-800 text-slate-200 transition-colors flex items-center gap-2"
            >
              <Mic className="w-4 h-4 text-amber-400" />
              <span>Admin Voice Forge</span>
            </Link>
          </nav>
        </header>

        <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
          {children}
        </main>

        <footer className="border-t border-mandapa-800 bg-mandapa-900 py-4 px-6 text-center text-xs text-slate-400">
          Vāgdhenu Goṣṭhī Studio • Built with Next.js 14, IndicF5 DiT, Seed-VC & Spotify Pedalboard
        </footer>
      </body>
    </html>
  );
}
