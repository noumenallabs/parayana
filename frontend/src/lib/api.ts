/**
 * Vāgdhenu Goṣṭhī Studio — Typed Frontend API Client
 */

export interface Verse {
  id: string;
  project_id: string;
  verse_index: number;
  section_label: string;
  unit_type: string;
  choreography_override?: string | null;
  raw_text: string;
  kannada_text: string;
  slp1_text: string;
  iast_text?: string | null;
  lg_signature?: string | null;
  syllable_count: number;
  detected_meter?: string | null;
  override_meter?: string | null;
  apply_internal_sandhi: boolean;
  base_seed: number;
  hemistich_split_sec?: number | null;
  breath_windows_sec_json?: string | null;
  expected_duration_sec?: number | null;
  actual_duration_sec?: number | null;
  qc_status: "PENDING" | "PASS" | "FAIL" | "SILENCE_FLAG" | "DURATION_FLAG";
  qc_notes?: string | null;
  mixed_verse_wav_path?: string | null;
}

export interface Project {
  id: string;
  title: string;
  raw_input_text: string;
  render_mode: "preview_dsp" | "studio_seedvc";
  active_persona_ids: string[];
  chant_speed: number;
  nfe_steps: number;
  cfg_strength: number;
  tanpura_gain_db: number;
  reverb_wet: number;
  inter_verse_pause_sec: number;
  section_pause_sec: number;
  choreography_mode: "AUTO_LITURGICAL" | "ANTIPHONAL_CALL_RESPONSE" | "FULL_UNISON";
  retain_intermediate_stems: boolean;
  status: "PENDING" | "RENDERING" | "COMPLETED" | "PAUSED" | "FAILED";
  master_wav_path?: string | null;
  lrc_path?: string | null;
  srt_path?: string | null;
  split_tracks_zip_path?: string | null;
  video_mp4_path?: string | null;
  verses: Verse[];
}

export interface Persona {
  id: string;
  name: string;
  role_tag: string;
  creation_mode: string;
  recipe_json?: string | null;
  ref_wav_path: string;
  cached_tensors_path: string;
  default_pan: number;
  default_gain_db: number;
}

export interface MasterExportResponse {
  project_id: string;
  master_wav_url: string;
  lrc_url: string;
  srt_url: string;
  stems_zip_url?: string | null;
  split_tracks_zip_url?: string | null;
  lufs: number;
  peak_dbtp: number;
}

const API_BASE = "";

export async function createProject(payload: {
  title: string;
  raw_input_text: string;
  japa_repeat_count?: number | null;
  render_mode?: string;
  chant_speed?: number;
  tanpura_gain_db?: number;
  reverb_wet?: number;
  inter_verse_pause_sec?: number;
  choreography_mode?: string;
}): Promise<Project> {
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listProjects(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/projects`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateVerse(
  projectId: string,
  verseIndex: number,
  updates: {
    override_meter?: string | null;
    choreography_override?: string | null;
    apply_internal_sandhi?: boolean;
    base_seed?: number;
  }
): Promise<Verse> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/verses/${verseIndex}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function renderProject(projectId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/render`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function pauseProject(projectId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/pause`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function rerollVerse(projectId: string, verseIndex: number): Promise<Verse> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/verses/${verseIndex}/reroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seed_offset: 101 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function masterProject(
  projectId: string,
  options?: {
    tanpura_gain_db?: number;
    reverb_wet?: number;
    inter_verse_pause_sec?: number;
  }
): Promise<MasterExportResponse> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/master`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options || {}),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportVideo(
  projectId: string,
  options?: { font_size?: number; background_color?: string }
): Promise<{ status: string; video_mp4_url: string }> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/export-video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options || { font_size: 38 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listPersonas(): Promise<Persona[]> {
  const res = await fetch(`${API_BASE}/api/personas`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function forgePersona(data: {
  name: string;
  role_tag: string;
  prompt?: string;
  formant_shift_st: number;
  chest_db: number;
  presence_db: number;
  air_db: number;
  default_pan: number;
  default_gain_db: number;
}): Promise<Persona> {
  const res = await fetch(`${API_BASE}/api/personas/forge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function blendPersonas(data: {
  name: string;
  role_tag: string;
  parent_a_id: string;
  parent_b_id: string;
  alpha: number;
  default_pan: number;
  default_gain_db: number;
}): Promise<Persona> {
  const res = await fetch(`${API_BASE}/api/personas/blend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function subscribeProjectEvents(
  projectId: string,
  onEvent: (event: any) => void
): () => void {
  const evtSource = new EventSource(`${API_BASE}/api/projects/${projectId}/events`);
  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch (err) {
      console.error("SSE parse error", err);
    }
  };
  return () => {
    evtSource.close();
  };
}
