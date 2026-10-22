"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Play,
  Pause,
  Download,
  FileText,
  Video,
  Archive,
  Music,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import WaveSurfer from "wavesurfer.js";
import { MasterExportResponse, exportVideo, masterProject } from "@/lib/api";

interface MasterExportBarProps {
  projectId: string;
  isCompleted: boolean;
}

export default function MasterExportBar({ projectId, isCompleted }: MasterExportBarProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [masterData, setMasterData] = useState<MasterExportResponse | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isVideoExporting, setIsVideoExporting] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (waveformRef.current && masterData?.master_wav_url) {
      if (wavesurfer.current) {
        wavesurfer.current.destroy();
      }

      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "#3D4460",
        progressColor: "#FFB300",
        cursorColor: "#FFFFFF",
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        height: 64,
        url: masterData.master_wav_url,
      });

      wavesurfer.current.on("play", () => setIsPlaying(true));
      wavesurfer.current.on("pause", () => setIsPlaying(false));
      wavesurfer.current.on("finish", () => setIsPlaying(false));

      return () => {
        wavesurfer.current?.destroy();
      };
    }
  }, [masterData?.master_wav_url]);

  const handleAssembleMaster = async () => {
    setIsExporting(true);
    try {
      const res = await masterProject(projectId);
      setMasterData(res);
    } catch (err: any) {
      alert(`Mastering failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportVideo = async () => {
    setIsVideoExporting(true);
    try {
      const res = await exportVideo(projectId);
      setVideoUrl(res.video_mp4_url);
    } catch (err: any) {
      alert(`Video export failed: ${err.message}`);
    } finally {
      setIsVideoExporting(false);
    }
  };

  const togglePlay = () => {
    if (wavesurfer.current) {
      wavesurfer.current.playPause();
    }
  };

  return (
    <div className="bg-mandapa-900 border border-mandapa-800 rounded-xl p-5 shadow-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-mandapa-800 pb-3">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Music className="w-5 h-5 text-mandapa-gold" />
            <span>Master Deliverables & Multi-Platform Export Bar</span>
          </h2>
          <p className="text-xs text-slate-400">
            Standard: 48 kHz / 24-bit Stereo WAV (-14.0 LUFS, -1.0 dBTP) • Synced SRT & LRC
          </p>
        </div>

        <button
          type="button"
          onClick={handleAssembleMaster}
          disabled={isExporting}
          className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs flex items-center gap-2 disabled:opacity-50 transition-all shadow-md shadow-amber-500/10"
        >
          {isExporting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Mastering Bus (-14 LUFS)...</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="w-4 h-4 fill-slate-950" />
              <span>Assemble & Master Audio</span>
            </>
          )}
        </button>
      </div>

      {/* Waveform Player */}
      {masterData?.master_wav_url && (
        <div className="bg-mandapa-950/80 border border-mandapa-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={togglePlay}
                className="w-10 h-10 rounded-full bg-mandapa-gold text-slate-950 flex items-center justify-center hover:bg-amber-400 transition-colors shadow-md shadow-amber-500/20"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
              </button>
              <div>
                <div className="font-semibold text-white text-sm">Master Chanting Bus</div>
                <div className="text-[11px] font-mono text-slate-400">
                  Loudness: <span className="text-mandapa-gold">{masterData.lufs.toFixed(1)} LUFS</span> • Peak: <span className="text-slate-200">{masterData.peak_dbtp.toFixed(1)} dBTP</span>
                </div>
              </div>
            </div>

            <div className="px-2.5 py-1 rounded bg-mandapa-800 text-[11px] font-mono text-emerald-400 border border-emerald-500/20">
              EBU R128 Compliant
            </div>
          </div>

          <div ref={waveformRef} className="cursor-pointer" />
        </div>
      )}

      {/* 1-Click Download Actions */}
      {masterData && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-1">
          {/* Master 48kHz WAV */}
          <a
            href={masterData.master_wav_url}
            download
            className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5"
          >
            <Download className="w-4 h-4 text-mandapa-gold" />
            <span className="text-xs font-semibold">Master WAV</span>
            <span className="text-[10px] text-slate-400">48kHz / 24-bit</span>
          </a>

          {/* SRT Subtitles */}
          <a
            href={masterData.srt_url}
            download
            className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5"
          >
            <FileText className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-semibold">Subtitles (.SRT)</span>
            <span className="text-[10px] text-slate-400">Verse Timings</span>
          </a>

          {/* LRC Lyrics */}
          <a
            href={masterData.lrc_url}
            download
            className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5"
          >
            <FileText className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-semibold">Lyrics (.LRC)</span>
            <span className="text-[10px] text-slate-400">Media Players</span>
          </a>

          {/* FLAC Stems */}
          {masterData.stems_zip_url && (
            <a
              href={masterData.stems_zip_url}
              download
              className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5"
            >
              <Archive className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold">Stems (.ZIP)</span>
              <span className="text-[10px] text-slate-400">Lossless FLAC</span>
            </a>
          )}

          {/* Spotify Split Tracks */}
          {masterData.split_tracks_zip_url && (
            <a
              href={masterData.split_tracks_zip_url}
              download
              className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5"
            >
              <Music className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold">Spotify Album</span>
              <span className="text-[10px] text-slate-400">Split Tracks (.ZIP)</span>
            </a>
          )}

          {/* 1080p Video Exporter */}
          <button
            type="button"
            onClick={handleExportVideo}
            disabled={isVideoExporting}
            className="flex flex-col items-center justify-center p-3 rounded-lg bg-mandapa-950 border border-mandapa-800 hover:border-mandapa-gold/50 text-slate-200 transition-all text-center gap-1.5 disabled:opacity-50"
          >
            {isVideoExporting ? (
              <RefreshCw className="w-4 h-4 animate-spin text-mandapa-gold" />
            ) : (
              <Video className="w-4 h-4 text-rose-400" />
            )}
            <span className="text-xs font-semibold">1080p Video</span>
            <span className="text-[10px] text-slate-400">
              {videoUrl ? "Ready (.MP4)" : "Generate MP4"}
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
