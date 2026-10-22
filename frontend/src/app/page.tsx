"use client";

import React, { useEffect, useState } from "react";
import StotraInputPanel from "@/components/StotraInputPanel";
import EnsembleMixerRack from "@/components/EnsembleMixerRack";
import VerseQueueTable from "@/components/VerseQueueTable";
import MasterExportBar from "@/components/MasterExportBar";
import {
  Project,
  createProject,
  getProject,
  listProjects,
  pauseProject,
  renderProject,
  rerollVerse,
  subscribeProjectEvents,
  updateVerse,
} from "@/lib/api";

export default function StudioHomePage() {
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [rerollingIndex, setRerollingIndex] = useState<number | null>(null);

  // Load latest project on mount if any
  useEffect(() => {
    async function loadLatest() {
      try {
        const projs = await listProjects();
        if (projs && projs.length > 0) {
          const full = await getProject(projs[0].id);
          setCurrentProject(full);
        }
      } catch (err) {
        console.error("Failed to load projects", err);
      }
    }
    loadLatest();
  }, []);

  // Subscribe to real-time SSE render updates
  useEffect(() => {
    if (!currentProject?.id) return;

    const unsubscribe = subscribeProjectEvents(currentProject.id, (event) => {
      if (event.type === "verse_completed" || event.type === "verse_rerolled") {
        setCurrentProject((prev) => {
          if (!prev) return prev;
          const updatedVerses = prev.verses.map((v) =>
            v.verse_index === event.verse_index
              ? {
                  ...v,
                  qc_status: event.qc_status,
                  actual_duration_sec: event.duration_sec || v.actual_duration_sec,
                  mixed_verse_wav_path: event.mixed_wav_url,
                }
              : v
          );
          return { ...prev, verses: updatedVerses };
        });
      } else if (event.type === "project_render_finished") {
        setIsRendering(false);
        setCurrentProject((prev) => (prev ? { ...prev, status: "COMPLETED" } : prev));
      } else if (event.type === "project_paused") {
        setIsRendering(false);
        setCurrentProject((prev) => (prev ? { ...prev, status: "PAUSED" } : prev));
      }
    });

    return () => {
      unsubscribe();
    };
  }, [currentProject?.id]);

  const handleCreateProject = async (payload: any) => {
    setIsLoading(true);
    try {
      const proj = await createProject(payload);
      setCurrentProject(proj);
    } catch (err: any) {
      alert(`Failed to create project: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartRender = async () => {
    if (!currentProject) return;
    setIsRendering(true);
    try {
      await renderProject(currentProject.id);
    } catch (err: any) {
      alert(`Render failed: ${err.message}`);
      setIsRendering(false);
    }
  };

  const handlePauseRender = async () => {
    if (!currentProject) return;
    try {
      await pauseProject(currentProject.id);
      setIsRendering(false);
    } catch (err: any) {
      alert(`Pause failed: ${err.message}`);
    }
  };

  const handleRerollVerse = async (verseIndex: number) => {
    if (!currentProject) return;
    setRerollingIndex(verseIndex);
    try {
      const updated = await rerollVerse(currentProject.id, verseIndex);
      setCurrentProject((prev) => {
        if (!prev) return prev;
        const updatedVerses = prev.verses.map((v) =>
          v.verse_index === verseIndex ? updated : v
        );
        return { ...prev, verses: updatedVerses };
      });
    } catch (err: any) {
      alert(`Re-roll failed: ${err.message}`);
    } finally {
      setRerollingIndex(null);
    }
  };

  const handleUpdateMeter = async (verseIndex: number, meter: string) => {
    if (!currentProject) return;
    try {
      const updated = await updateVerse(currentProject.id, verseIndex, {
        override_meter: meter,
      });
      setCurrentProject((prev) => {
        if (!prev) return prev;
        const updatedVerses = prev.verses.map((v) =>
          v.verse_index === verseIndex ? updated : v
        );
        return { ...prev, verses: updatedVerses };
      });
    } catch (err: any) {
      alert(`Failed to update meter: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stotra Input & Segmentation Panel */}
      <StotraInputPanel onProjectCreated={handleCreateProject} isLoading={isLoading} />

      {currentProject && (
        <>
          {/* 5-Pandit Ensemble Mixer Stage */}
          <EnsembleMixerRack
            renderMode={currentProject.render_mode}
            onRenderModeChange={(mode) =>
              setCurrentProject((prev) => (prev ? { ...prev, render_mode: mode } : prev))
            }
            chantSpeed={currentProject.chant_speed}
            onChantSpeedChange={(speed) =>
              setCurrentProject((prev) => (prev ? { ...prev, chant_speed: speed } : prev))
            }
            tanpuraGainDb={currentProject.tanpura_gain_db}
            onTanpuraGainChange={(gain) =>
              setCurrentProject((prev) => (prev ? { ...prev, tanpura_gain_db: gain } : prev))
            }
            reverbWet={currentProject.reverb_wet}
            onReverbWetChange={(wet) =>
              setCurrentProject((prev) => (prev ? { ...prev, reverb_wet: wet } : prev))
            }
            interVersePauseSec={currentProject.inter_verse_pause_sec}
            onInterVersePauseChange={(pause) =>
              setCurrentProject((prev) => (prev ? { ...prev, inter_verse_pause_sec: pause } : prev))
            }
            isRendering={isRendering || currentProject.status === "RENDERING"}
            onStartRender={handleStartRender}
            onPauseRender={handlePauseRender}
          />

          {/* Virtualized Verse Scansion & Queue Table */}
          <VerseQueueTable
            verses={currentProject.verses || []}
            onRerollVerse={handleRerollVerse}
            onUpdateMeter={handleUpdateMeter}
            rerollingIndex={rerollingIndex}
          />

          {/* Master Export Bar */}
          <MasterExportBar
            projectId={currentProject.id}
            isCompleted={currentProject.status === "COMPLETED"}
          />
        </>
      )}
    </div>
  );
}
