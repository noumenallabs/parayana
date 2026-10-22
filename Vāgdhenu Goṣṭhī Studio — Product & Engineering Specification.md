# **Vāgdhenu Goṣṭhī Studio — Product & Engineering Specification**

1. **Target Platform**: Apple MacBook Pro (M3 Pro, 36 GB Unified Memory, macOS Sonoma/Sequoia)  
   **Frontend Architecture**: Next.js 14 (App Router, TypeScript, Tailwind CSS, WaveSurfer.js, TanStack Virtual)  
   **Backend Architecture**: Python 3.10, FastAPI, SQLite (WAL Mode), PyTorch (`mps`), [prathoshap/vagdhenu](https://github.com/prathoshap/vagdhenu), [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc), [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts), [spotify/pedalboard](https://github.com/spotify/pedalboard), `pyloudnorm`**Master Deliverable Standard**: `48 kHz / 24-bit Stereo WAV` (`-14.0 LUFS`, `-1.0 dBTP`) \+ Synchronized `.srt` and `.lrc` Timing Tracks

# **1\. Architectural Invariants & Engineering Standards**

2. **Sequential Milestone Delivery**: Every User Story (`US-01` through `US-10`) scopes a strictly bounded set of files and a deterministic verification suite (`tests/verify_usXX_*.py`). A story is complete only when its verification script exits with status code `0` and outputs `VERIFY_PASS`.  
3. **Source-Pinned TTS & Vocoder Dependencies**: The published PyPI `f5-tts` package is incompatible with Vāgdhenu checkpoints ([Hysen Labs Analysis](https://hysenlabs.com/projects/prathoshap-vagdhenu)). The environment must install the editable local clone of [AI4Bharat/IndicF5](https://huggingface.co/ai4bharat/IndicF5) (`vendor/IndicF5`) and load `NVIDIA/BigVGAN` from `vendor/BigVGAN` ([Vāgdhenu GitHub](https://github.com/prathoshap/vagdhenu)).  
4. **Apple Silicon (`mps`) Mixed-Precision Discipline**: Set `PYTORCH_ENABLE_MPS_FALLBACK=1` across all backend processes. Keep the `RMVPE` pitch extractor (`rmvpe.pt`) in `float32` (`is_half=False`) as implemented in [Seed-VC inference.py](https://github.com/Plachtaa/seed-vc/blob/main/inference.py) to prevent complex STFT `NaN` overflow on Apple Metal.  
5. **Unison Tonic Pitch Lock (`138.59 Hz` / `C#3`)**: The [Vāgdhenu training corpus](https://huggingface.co/datasets/prathoshap/vagdhenu-data) is anchored to a `C#3` (`138.59 Hz`) *ādhāra-ṣaḍja* tanpura drone ([Benchmark Report](https://github.com/hemanth/sanskrit-tts-web/blob/main/benchmark.md)). Every voice conversion pass in [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc) must enforce `f0_condition=True`, `auto_f0_adjust=False`, and `semi_tone_shift=0` ([Seed-VC CLI Docs](https://deepwiki.com/Plachtaa/seed-vc/3.1-command-line-interface)) so all virtual pandits remain locked in unison pitch.  
6. **Classical (*Laukika*) Orthographic Normalization**: [Vāgdhenu](https://prathosh.in/vagdhenu/) synthesizes classical metrical *chandas* and prose (*gadya*) rather than Vedic *svara* pitch accents ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)). All Vedic accent codepoints (`U+0951`–`U+0954`, `U+1CD0`–`U+1CFF`, `U+A8E0`–`U+A8FF`) must be stripped prior to running `src/prep_text.py`.  
7. **Single-Śloka Synthesis Window**: Never feed more than one śloka (two hemistichs) into a single Vāgdhenu forward pass ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)). Multi-verse *Sahasranāmas* (108–160+ verses) must be segmented into discrete `VerseUnit` records, synthesized sequentially with disk checkpointing, and assembled at the mastering stage.  
8. **In-Memory Singleton Model Lifecycle**: Hold both `Vāgdhenu` (\~2.5 GB) and `Seed-VC` (\~2.6 GB) persistently in Unified Memory inside the FastAPI worker rather than spawning per-verse CLI subprocesses.

# **2\. System Resource Budget (MacBook Pro M3 Pro — 36 GB Unified Memory)**

| Subsystem / Model | Precision | Device | Resident RAM | Lifecycle |
| :---- | :---- | :---- | :---- | :---- |
| **macOS \+ Next.js 14 Server \+ Browser** | N/A | CPU / GPU | \~6.0 GB | Always active |
| **Vāgdhenu DiT (`IndicF5` 337M) \+ `BigVGAN-v2` (112M)** | `float16 / float32` | `mps` | \~2.5 GB | Persistent singleton in `chant_worker.py` ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)) |
| **Seed-VC Singing (`Whisper-base` \+ `RMVPE` \+ `CAMPPlus` \+ `UViT-DiT` \+ `BigVGAN`)** | `float16 (RMVPE fp32)` | `mps` | \~2.6 GB | Persistent singleton in `vc_worker.py` ([Seed-VC inference.py](https://github.com/Plachtaa/seed-vc/blob/main/inference.py)) |
| **Pre-Cached Pandit Persona Tensors (5–10 Voices)** | `float32` | `mps` | \~0.2 GB | Cached `(S_ori, mel2, F0_ori, style2)` `.pt` files |
| **Indic Parler-TTS (`ai4bharat/indic-parler-tts`, 0.9B)** | `float16` | `mps` | \~2.2 GB | Loaded on-demand in Admin Voice Forge; freed via `torch.mps.empty_cache()` |
| **Audio Buffers & Pedalboard Mastering (`48 kHz float32`)** | `float32` | CPU | \~1.5 GB | Active during verse mixing & Sahasranāma stitching |
| **Peak Unified Memory Footprint** | — | Unified | **\~15.0 GB / 36.0 GB** | Retains **21.0 GB** free memory headroom |

# **3\. Monorepo File Tree**

```
vagdhenu-gosthi-studio/
├── Makefile
├── backend/
│   ├── requirements.txt
│   ├── config.py
│   ├── db.py
│   ├── schemas.py
│   ├── main.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── stotra_parser.py
│   │   ├── voice_forge.py
│   │   ├── chant_worker.py
│   │   ├── vc_worker.py
│   │   └── mixer.py
│   ├── scripts/
│   │   ├── setup_m3.sh
│   │   ├── generate_acoustics.py
│   │   └── seed_default_pandits.py
│   ├── tests/
│   │   ├── verify_us01_env.py
│   │   ├── verify_us02_db.py
│   │   ├── verify_us03_parser.py
│   │   ├── verify_us04_voice_forge.py
│   │   ├── verify_us05_chant_worker.py
│   │   ├── verify_us06_vc_worker.py
│   │   ├── verify_us07_mixer.py
│   │   └── verify_us08_api.py
│   └── storage/
│       ├── studio.db
│       ├── weights/
│       ├── personas/
│       ├── acoustics/
│       └── projects/
└── frontend/
    ├── package.json
    ├── next.config.mjs
    └── src/
        ├── lib/api.ts
        ├── app/layout.tsx
        ├── app/page.tsx
        ├── app/admin/voices/page.tsx
        └── components/
            ├── StotraInputPanel.tsx
            ├── VerseQueueTable.tsx
            ├── EnsembleMixerRack.tsx
            ├── VoiceForgeLab.tsx
            └── MasterExportBar.tsx
```

# **4\. Epics & User Stories (Implementation & Verification Roadmap)**

## **Epic 1: Core Infrastructure & Persistence Layer**

### **US-01: Apple Silicon (mps) Runtime, Model Weights & Acoustic Reference Setup**

9. **User Story: As a system administrator setting up the studio on an M3 Pro MacBook, I want a single bootstrap script that provisions the Python 3.10 MPS environment, clones the required source repositories, downloads all model checkpoints, and synthesizes reference acoustic beds so the audio engine runs offline with zero external asset dependencies.**  
10. **Target Files: backend/scripts/setup\_m3.sh, backend/scripts/generate\_acoustics.py, backend/config.py, backend/tests/verify\_us01\_env.py**  
11. **Technical Specification:**  
    1. **setup\_m3.sh: Creates .venv (Python 3.10), installs PyTorch (mps), clones [prathoshap/vagdhenu](https://github.com/prathoshap/vagdhenu) into backend/vendor/vagdhenu, clones [AI4Bharat/IndicF5](https://huggingface.co/ai4bharat/IndicF5) into backend/vendor/IndicF5 (pip install \-e vendor/IndicF5), clones NVIDIA/BigVGAN into backend/vendor/BigVGAN, and clones [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc) into backend/vendor/seed-vc.**  
    2. **Downloads checkpoints from [prathoshap/vagdhenu](https://huggingface.co/prathoshap/vagdhenu) (voice\_steer\_ema\_2026-06-17.pt, voice\_armA\_ema\_2026-06-11.pt, voc\_bigvgan\_EMA\_2026-06-11.pth) into backend/storage/weights/vagdhenu/.**  
    3. **generate\_acoustics.py: Synthesizes a phase-continuous 60-second stereo 48 kHzSa–Pa–Sa tanpura drone locked to 138.5913 Hz (C\#3) and 207.6523 Hz (G\#3) (storage/acoustics/csharp3\_tanpura\_48k.wav) and a stereo stone maṇḍapa impulse response (storage/acoustics/temple\_mandapa\_ir\_48k.wav, RT60 \= 1.35s).**  
    4. **config.py: Registers vendor/vagdhenu/src, vendor/BigVGAN, and vendor/seed-vc on sys.path and exports typed path constants.**  
12. **Acceptance Criteria:**  
    1. **GIVEN a clean macOS M3 Pro environment, WHENsetup\_m3.sh and generate\_acoustics.py complete, THEN PyTorch MPS is active, all Vāgdhenu weights exist on disk, and the 48 kHz stereo tanpura and impulse response WAV files are valid.**  
13. **Verification Gate (verify\_us01\_env.py):**  
    1. **Command: cd backend && source .venv/bin/activate && python tests/verify\_us01\_env.py**  
    2. **Assertions: Assert torch.backends.mps.is\_available(), assert weight files and 48 kHz stereo acoustic WAVs exist, import prep\_text from vendor/vagdhenu/src without error, and output VERIFY\_PASS: US-01.**

### **US-02: Resumable Project & Sahasranāma State Persistence**

14. **User Story: As a producer rendering a 150-verse Sahasranāma over a 90-minute session, I want every project, pandit persona, and individual verse state persisted in a concurrent SQLite database so that batch renders can pause, resume across sessions, and support single-verse re-rolls without losing progress.**  
15. **Target Files: backend/db.py, backend/schemas.py, backend/tests/verify\_us02\_db.py**  
16. **Technical Specification:**  
    1. **db.py: Configures storage/studio.db with PRAGMA journal\_mode=WAL; PRAGMA foreign\_keys=ON;, thread-safe connection pooling (check\_same\_thread=False), and three tables:**  
       1. **pandit\_personas: id, name, role\_tag, creation\_mode, recipe\_json, ref\_wav\_path, cached\_tensors\_path, default\_pan, default\_gain\_db, created\_at.**  
       2. **projects: id, title, raw\_input\_text, render\_mode (preview\_dsp or studio\_seedvc), active\_persona\_ids\_json, chant\_speed (0.90), nfe\_steps (64), cfg\_strength (3.0), tanpura\_gain\_db (-18.0), reverb\_wet (0.15), inter\_verse\_pause\_sec (0.85), section\_pause\_sec (1.60), status, master\_wav\_path, lrc\_path, srt\_path, created\_at.**  
       3. **verses: id, project\_id, verse\_index, section\_label, unit\_type (METRICAL\_SLOKA, GADYA\_PROSE, or JAPA\_REPEAT), raw\_text, kannada\_text, slp1\_text, lg\_signature, syllable\_count, detected\_meter, override\_meter, apply\_internal\_sandhi, base\_seed, expected\_duration\_sec, actual\_duration\_sec, qc\_status, qc\_notes, mixed\_verse\_wav\_path.**  
    2. **schemas.py: Defines Pydantic v2 contracts (PersonaCreateRequest, PersonaResponse, ProjectCreateRequest, VerseUpdateRequest, VerseResponse, ProjectDetailResponse, MasterExportRequest).**  
17. **Acceptance Criteria:**  
    1. **GIVEN an active project with 150 verses, WHEN a background worker updates verses.qc\_status while the UI polls project state, THEN zero SQLite lock contention occurs and all state transitions persist accurately.**  
18. **Verification Gate (verify\_us02\_db.py):**  
    1. **Command: python tests/verify\_us02\_db.py**  
    2. **Assertions: Assert PRAGMA journal\_mode \== "wal", insert 1 project with 108 verse records, execute concurrent read/write updates from two threads, verify foreign-key cascade deletion, and output VERIFY\_PASS: US-02.**

## **Epic 2: Sanskrit Phonological Frontend & Creative Voice Lab**

### **US-03: Multi-Verse Sahasranāma, Prose (Gadya) & Japa Mantra Parser**

19. **User Story: As a user pasting a complete Sanskrit Stotra, Sahasranāma, or Mantra in any Indian script, I want the system to automatically strip unsupported diacritics and verse numbers, segment the text into liturgical sections and individual verses, convert each verse into phonetic Kannada script with sandhi resolution, and detect the poetic meter (chandas) or prose chunk boundaries.**  
20. **Target Files: backend/engine/stotra\_parser.py, backend/tests/verify\_us03\_parser.py**  
21. **Technical Specification:**  
    1. **strip\_vedic\_and\_editorial(text: str): Strips Vedic tone marks (\[\\u0951-\\u0954\\u1CD0-\\u1CFF\\uA8E0-\\uA8FF\]), bracketed editorial comments, and trailing verse numbers (॥ १०८ ॥, \|\| 108 \|\|, 108.) ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
    2. **parse\_stotra\_or\_sahasranama(raw\_text: str, japa\_repeat\_count: Optional\[int\] \= None, apply\_sandhi: bool \= False):**  
       1. **Japa Repetition Mode: When japa\_repeat\_count is specified (11, 21, 54, or 108), groups a short mantra into 4 repetitions per unit across ceil(japa\_repeat\_count / 4\) units with base\_seed \= 100 \+ unit\_idx \* 29, preventing Vāgdhenu's collapse limit on more than 4 consecutive identical syllables ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
       2. **Section & Verse Segmentation: Detects liturgical section headers (पूर्वपीठिका, ध्यानम्, स्तोत्रम्, फलश्रुतिः) and splits metrical verses on double daṇḍas (॥) or blank lines, keeping full 2-hemistich verses intact so cross-quarter sandhi is never severed (E58 in [arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
       3. **Kannada Orthographic Routing & Meter Scansion: Invokes vendor/vagdhenu/src/prep\_text.py to output kannada\_text (preserving inherent vowels, jihvāmūlīya, upadhmānīya, homorganic anusvāra, daṇḍa-final visarga echo, and vocalic ṝ), lg\_signature (L/G syllable weights), syllable\_count, and detected\_meter across 18 classical meters ([Live Web App](https://h3manth.com/ai/sanskrit-tts/)).**  
       4. **Prose (Gadya) Chunking: Classifies non-metrical saṅkalpa/nyāsa blocks as GADYA\_PROSE and chunks them strictly on safe word boundaries (never after a halant् or sandhied vowel) into 10–14 akṣara breath groups ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
22. **Acceptance Criteria:**  
    1. **GIVEN a multi-section Sahasranāma text containing prose headers and metrical verses, WHEN parsed by stotra\_parser.py, THEN every unit is assigned an accurate section label, Kannada phonetic transcription, L/G signature, and meter classification.**  
23. **Verification Gate (verify\_us03\_parser.py):**  
    1. **Command: python tests/verify\_us03\_parser.py**  
    2. **Assertions: Assert Vedic marks and ॥ १ ॥ strip cleanly; assert वसुदेवसुतं देवं... scans as anushtubh (32 syllables); assert नारायणाय परिपूर्णगुणार्णवाय... scans as vasantatilaka (56 syllables); assert kannada\_text is in \\u0C80–\\u0CFF; assert japa\_repeat\_count=108 yields 27 units with distinct seeds; output VERIFY\_PASS: US-03.**

### **US-04: Admin Pandit Persona Forge & 192-D Speaker Embedding Blender**

24. **User Story: As an administrator curating the studio's vocal ensemble, I want to synthesize new Indian male vocal timbres from text descriptions, sculpt their vocal-tract formants and EQ, and blend speaker embeddings between voices so we can create proprietary pandit personas without cloning real individuals.**  
25. **Target Files: backend/engine/voice\_forge.py, backend/scripts/seed\_default\_pandits.py, backend/tests/verify\_us04\_voice\_forge.py**  
26. **Technical Specification:**  
    1. **generate\_parler\_reference(prompt: str, out\_wav\_path: str): Loads [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) onto mps in float16, synthesizes a 15-second studio calibration clip, writes 44.1 kHz mono WAV, and releases memory via gc.collect(); torch.mps.empty\_cache().**  
    2. **sculpt\_vocal\_tract(in\_wav: str, out\_wav: str, formant\_shift\_st: float, chest\_db: float, presence\_db: float, air\_db: float): Scales vocal-tract formants (-2.5 to \+2.5 semitones) via pyrubberband while keeping fundamental pitch fixed, followed by a 3-band EQ (LowShelfFilter(160 Hz), PeakFilter(1800 Hz), HighShelfFilter(4500 Hz)) in [spotify/pedalboard](https://github.com/spotify/pedalboard).**  
    3. **extract\_and\_cache\_seedvc\_tensors(ref\_wav\_path: str, out\_pt\_path: str, vc\_worker): Extracts and serializes {"S\_ori": S\_ori.cpu(), "mel2": mel2.cpu(), "F0\_ori": F0\_ori.cpu(), "style2": style2.cpu()} (style2 shape \[1, 192\]) using [Seed-VC inference.py](https://github.com/Plachtaa/seed-vc/blob/main/inference.py)'s CAMPPlus (funasr/campplus), Whisper, and RMVPE encoders.**  
    4. **blend\_personas(persona\_a\_pt: str, persona\_b\_pt: str, alpha: float, out\_pt\_path: str): Computes magnitude-preserving spherical linear interpolation (slerp) between style2\_A and style2\_B at ratio alpha (0.0 to 1.0).**  
    5. **seed\_default\_pandits.py: Provisions five default personas (pandit\_1\_mukhya Lead Center, pandit\_2\_vriddha Deep Elder \-1.4 st Center-Left, pandit\_3\_ghanapathi Bass-Baritone \-0.8 st Center-Right, pandit\_4\_yuva Bright Tenor \+1.1 st Far Left, and pandit\_5\_upagayaka Warm Support \+0.5 st Far Right).**  
27. **Acceptance Criteria:**  
    1. **GIVEN two parent personas or a text prompt, WHEN processed by voice\_forge.py, THEN a 44.1 kHz reference WAV and a pre-computed cached\_tensors.pt file (style2 shape \[1, 192\]) are saved and registered in SQLite.**  
28. **Verification Gate (verify\_us04\_voice\_forge.py):**  
    1. **Command: python tests/verify\_us04\_voice\_forge.py**  
    2. **Assertions: Assert all 5 default personas exist in SQLite and on disk, assert loaded style2 tensors have shape (1, 192), assert blend\_personas(..., alpha=0.5) produces a valid vector with cosine similarity in (0.40, 0.95) to both parents, and output VERIFY\_PASS: US-04.**

## **Epic 3: Multi-Pandit Synthesis, Voice Conversion & Mastering Pipeline**

### **US-05: Persistent Vāgdhenu \+ BigVGAN-v2 Synthesis & Self-Healing Quality Control**

29. **User Story: As a producer synthesizing Sanskrit verses on Apple Silicon, I want a persistent in-memory Vāgdhenu worker that generates stochastic multi-seed takes under the Half-Reference Rule and automatically re-seeds any take that fails duration or internal-silence quality checks.**  
30. **Target Files: backend/engine/chant\_worker.py, backend/tests/verify\_us05\_chant\_worker.py**  
31. **Technical Specification:**  
    1. **ChantWorker singleton: Loads voice\_steer\_ema\_2026-06-17.pt (337M DiT) and voc\_bigvgan\_EMA\_2026-06-11.pth (112M BigVGAN-v2 with use\_cuda\_kernel=False) onto torch.device("mps") once at startup ([Hugging Face Model Card](https://huggingface.co/prathoshap/vagdhenu)).**  
    2. **synthesize\_verse\_takes(verse: VerseRow, num\_takes: int, nfe: int \= 64, cfg: float \= 3.0, speed: float \= 0.90):**  
       1. **Selects the meter-matched reference clip from Vāgdhenu's reference bank under the Half-Reference Rule ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
       2. **Renders 1 take in preview\_dsp mode (nfe=48) or K independent takes in studio\_seedvc mode (seed\_i \= verse.base\_seed \+ i \* 37, nfe=64, cfg \= 2.8 \+ i \* 0.1) to create natural consonant micro-timing variance (15–35 ms) across pandits ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
       3. **Applies the fricative- and stop-aware onset/tail post-gate ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
    3. **run\_qc\_gates(audio\_24k: np.ndarray, expected\_dur: float):**  
       1. **Duration Gate: Requires actual\_dur to fall within 75% to 125% of expected\_dur.**  
       2. **Internal Silence Gate: Scans 20 ms RMS frames inside each hemistich and flags FLAG\_SILENCE if any spurious mid-pāda pause exceeds 180 ms (Section 9 of [arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)).**  
       3. **Automatically retries up to 3 backup seeds (base\_seed \+ 101, \+202, \+303) on QC failure.**  
32. **Acceptance Criteria:**  
    1. **GIVEN a scanned VerseRow, WHENsynthesize\_verse\_takes runs with num\_takes=2, THEN two 24 kHz WAV files pass QC with aligned syllable durations and distinct stochastic micro-timings.**  
33. **Verification Gate (verify\_us05\_chant\_worker.py):**  
    1. **Command: python tests/verify\_us05\_chant\_worker.py**  
    2. **Assertions: Synthesize वसुदेवसुतं देवं... with num\_takes=2; assert both 24 kHz WAVs exist, pass QC (qc\_status \== "PASS"), have duration in \[7.0s, 13.0s\], and exhibit envelope correlation between 0.80 and 0.999; output VERIFY\_PASS: US-05.**

### **US-06: Dual-Mode Ensemble Converter (Fast DSP Preview & F0-Locked Seed-VC Master)**

34. **User Story: As a producer, I want to toggle between a Fast Preview mode (instant DSP ensemble for proofreading 150 verses quickly) and a Studio Master mode (neural Seed-VC conversion into 5 distinct pandit voices locked to the 138.59 Hz tonic pitch).**  
35. **Target Files: backend/engine/vc\_worker.py, backend/tests/verify\_us06\_vc\_worker.py**  
36. **Technical Specification:**  
    1. **VCWorker singleton: Loads [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc/blob/main/inference.py) (DiT\_seed\_v2\_uvit\_whisper\_base\_f0\_44k\_bigvgan\_pruned\_ft\_ema\_v2.pth, rmvpe.pt with is\_half=False, campplus\_cn\_common.bin, and BigVGAN) onto torch.device("mps").**  
    2. **render\_preview\_dsp\_stems(base\_take\_wav: str, personas: List\[PersonaRow\], out\_dir: str): Generates K stems in under 0.2s by applying human onset micro-delays (\[0, 19, 27, 34, 41\] ms), pitch micro-detuning (\[0, \-5, \+4, \-7, \+6\] cents), and per-persona formant shifts.**  
    3. **render\_studio\_seedvc\_stems(take\_wavs: List\[str\], personas: List\[PersonaRow\], out\_dir: str): Converts each take i using persona\[i\].cached\_tensors\_path with locked unison parameters: f0\_condition=True, auto\_f0\_adjust=False, semi\_tone\_shift=0, diffusion\_steps=40, inference\_cfg\_rate=0.7, length\_adjust=1.0, fp16=True ([Seed-VC CLI Docs](https://deepwiki.com/Plachtaa/seed-vc/3.1-command-line-interface)).**  
37. **Acceptance Criteria:**  
    1. **GIVEN multiple Vāgdhenu seed takes and distinct Pandit Personas, WHEN converted in studio\_seedvc mode, THEN all output stems share the exact same median fundamental pitch (138.59 HzC\#3) while exhibiting distinct vocal-tract spectral envelopes.**  
38. **Verification Gate (verify\_us06\_vc\_worker.py):**  
    1. **Command: python tests/verify\_us06\_vc\_worker.py**  
    2. **Assertions: Convert 2 takes into pandit\_1\_mukhya and pandit\_2\_vriddha across both modes; assert median voiced F0 of both studio\_seedvc stems matches within 2.5 Hz while MFCC cosine distance exceeds 0.05; output VERIFY\_PASS: US-06.**

### **US-07: Semicircle Spatial Mixer, C\#3 Tanpura Bed, \-14 LUFS Master & Synced Lyrics**

39. **User Story: As a publisher preparing releases for YouTube and Spotify, I want the system to pan the pandit stems across a stereo semicircle inside a shared temple acoustic space, layer a continuous C\#3 tanpura drone, normalize loudness to \-14.0 LUFS at 48 kHz / 24-bit, and export synchronized SRT and LRC lyric files.**  
40. **Target Files: backend/engine/mixer.py, backend/tests/verify\_us07\_mixer.py**  
41. **Technical Specification:**  
    1. **mix\_single\_verse(stem\_wavs: List\[str\], personas: List\[PersonaRow\], reverb\_wet: float, out\_wav: str):**  
       1. **Resamples stems to 48000 Hz (float32), calibrates active voice RMS (where absolute amplitude exceeds 0.015) to \-18.0 dBFS ([Benchmark Report](https://github.com/hemanth/sanskrit-tts-web/blob/main/benchmark.md)), applies persona.default\_gain\_db, and pans across \[-0.45, \-0.22, 0.0, \+0.22, \+0.45\] via constant-power panning.**  
       2. **Routes the stereo bus through [spotify/pedalboard](https://github.com/spotify/pedalboard): HighpassFilter(85 Hz), LowShelfFilter(180 Hz, \-1.5 dB), Convolution("storage/acoustics/temple\_mandapa\_ir\_48k.wav", mix=reverb\_wet), and Compressor(threshold\_db=-16.0, ratio=2.5).**  
    2. **assemble\_project\_master(project\_id: str):**  
       1. **Concatenates all verse stereo WAVs with inter\_verse\_pause\_sec (0.85s) between verses and section\_pause\_sec (1.60s) between sections.**  
       2. **Mixes csharp3\_tanpura\_48k.wav at tanpura\_gain\_db (-18.0 dB) with a 1.5s lead-in and 2.5s cosine fade-out.**  
       3. **Normalizes integrated loudness to \-14.0 LUFS via pyloudnorm.Meter(48000) followed by pedalboard.Limiter(threshold\_db=-1.0).**  
       4. **Writes master\_48k\_24bit.wav (PCM\_24), lyrics.srt, lyrics.lrc, and stems.zip.**  
42. **Acceptance Criteria:**  
    1. **GIVEN a completed multi-verse project, WHENassemble\_project\_master executes, THEN it produces a 48 kHz / 24-bit stereo WAV measuring \-14.0 ± 0.5 LUFS with true peak at or below \-1.0 dBTP alongside valid .srt and .lrc timing files.**  
43. **Verification Gate (verify\_us07\_mixer.py):**  
    1. **Command: python tests/verify\_us07\_mixer.py**  
    2. **Assertions: Assert output WAV is 48000 Hz, 2 channels, PCM\_24; assert pyloudnorm integrated loudness is within \[-14.5, \-13.5\] LUFS and peak amplitude is at or below 0.892; assert .srt and .lrc files contain timestamps for every verse; output VERIFY\_PASS: US-07.**

## **Epic 4: API Layer & Next.js 14 Studio Interface**

### **US-08: FastAPI Control Plane & Real-Time SSE Render Queue**

44. **User Story: As a frontend client, I want REST endpoints to create projects, override per-verse meters, trigger single-verse seed re-rolls, and subscribe to a Server-Sent Events (SSE) stream so the UI updates live as each verse finishes rendering.**  
45. **Target Files: backend/main.py, backend/tests/verify\_us08\_api.py**  
46. **Technical Specification:**  
    1. **Implements POST /api/projects, GET /api/projects/{id}, PATCH /api/projects/{id}/verses/{v\_idx}, POST /api/projects/{id}/render, POST /api/projects/{id}/pause, POST /api/projects/{id}/verses/{v\_idx}/reroll, POST /api/projects/{id}/master, GET /api/projects/{id}/events (SSE), GET /api/personas, and POST /api/personas/forge.**  
    2. **Serves /audio/\* with HTTP Range support for WaveSurfer.js waveform scrubbing.**  
47. **Acceptance Criteria:**  
    1. **GIVEN the running FastAPI server, WHEN a client submits a stotra, patches a verse meter, renders, re-rolls a single verse, and requests mastering, THEN all endpoints return 200 OK and stream real-time SSE progress events.**  
48. **Verification Gate (verify\_us08\_api.py):**  
    1. **Command: python tests/verify\_us08\_api.py**  
    2. **Assertions: Execute full lifecycle via FastAPI TestClient and output VERIFY\_PASS: US-08.**

### **US-09: Next.js 14 Stotra Studio & Virtualized Sahasranāma Workspace**

49. **User Story: As a user producing a Stotra or Sahasranāma, I want a web interface where I can paste Sanskrit text, inspect the Guru/Laghu syllable scan and Kannada routing across 150+ verses, audition or re-roll individual verses as they render, adjust the 5-pandit semicircle mix, and download the mastered audio and lyrics.**  
50. **Target Files: frontend/package.json, frontend/next.config.mjs, frontend/src/lib/api.ts, frontend/src/app/layout.tsx, frontend/src/app/page.tsx, frontend/src/components/StotraInputPanel.tsx, frontend/src/components/VerseQueueTable.tsx, frontend/src/components/EnsembleMixerRack.tsx, frontend/src/components/MasterExportBar.tsx**  
51. **Technical Specification:**  
    1. **StotraInputPanel.tsx: Multi-script input editor \+ mode selector (Sahasranāma / Stotra vs. Japa 11x/21x/54x/108x) \+ "Scan & Segment Verses" action.**  
    2. **VerseQueueTable.tsx: Virtualized list (@tanstack/react-virtual) displaying Verse \#, section badge, Devanagari text, collapsible Kannada phonetic routing string, Guru/Laghu (ˉ / ˘) scansion badge, meter override dropdown (18 vṛttas \+ gadya), QC status badge, inline audio player, and 1-click "Re-Roll Seed (↻)" button.**  
    3. **EnsembleMixerRack.tsx: Mode switch (⚡ Fast Preview DSP vs. 🎙️ Studio Master Seed-VC), 5-pandit semicircle stage (-45° to \+45° pan \+ gain trim \+ solo/mute), and sliders for C\#3 Tanpura Level, Mandapa Reverb, Chant Pace, and Inter-Verse Pause.**  
    4. **MasterExportBar.tsx: WaveSurfer.js master waveform player with verse markers and 1-click downloads for 48kHz/24-bit WAV, .SRT, .LRC, and Stems .ZIP.**  
52. **Verification Gate:**  
    1. **Command: cd frontend && npm install && npm run typecheck && npm run build**  
    2. **Assertions: Zero TypeScript or Next.js production build errors.**

### **US-10: Next.js 14 Admin Voice Forge UI (/admin/voices) & Unified Build Automation**

53. **User Story: As an administrator, I want a dedicated web studio to design new pandit voices via Parler-TTS text prompts, sculpt vocal-tract formants and EQ, blend two existing pandit embeddings with a slider, and audition the result on a sample śloka before saving.**  
54. **Target Files: frontend/src/app/admin/voices/page.tsx, frontend/src/components/VoiceForgeLab.tsx, Makefile**  
55. **Technical Specification:**  
    1. **VoiceForgeLab.tsx: Two-tab voice design interface:**  
       1. **Tab 1 (Text-to-Persona Designer): Prompt input, role tag selector, formant shift slider (-2.5 to \+2.5 st), 3-band EQ sliders (160 Hz chest, 1.8 kHz nasal presence, 4.5 kHz air), and "Synthesize & Audition on Sample Śloka" button.**  
       2. **Tab 2 (CAMPPlus 192-D Embedding Blender): Parent A and Parent B selectors, 0%–100%slerp blend slider, and "Save Blended Persona" button.**  
    2. **Makefile: Defines make setup, make verify-all (executes verify\_us01 through verify\_us08 \+ npm run build), and make dev (starts FastAPI under macOS caffeinate \-i to prevent M3 Pro idle sleep throttling during long Sahasranāma renders alongside Next.js).**  
56. **Verification Gate:**  
    1. **Command: make verify-all**  
    2. **Assertions: All 8 Python verification suites and the Next.js production build pass sequentially.**

# **5\. M3 Pro Throughput Benchmarks**

| Production Workload | Unit Count | Fast Preview (preview\_dsp) | Studio Master (studio\_seedvc, 5 Pandits) | Master Assembly (-14 LUFS) |
| :---- | :---- | :---- | :---- | :---- |
| **Single Śloka / Mantra Audition** | **1 verse** | **\~16 sec** | **\~42 sec** | **Under 1 sec** |
| **Aṣṭakam (Śivāṣṭakam, Bhaja Govindam)** | **8–15 verses** | **\~2.5–4 mins** | **\~6–10 mins** | **\~1.5 sec** |
| **Japa Mālā (108× Short Mantra, 27 × 4 reps)** | **27 units** | **\~7 mins** | **\~18 mins** | **\~2 sec** |
| **Full Sahasranāma (Viṣṇu / Lalitā Sahasranāma)** | **\~145 verses** | **\~38 mins** | **\~95 mins (resumable per-verse)** | **\~4 sec** |

  \* \*\*Command\*\*: \`make verify-all\`

# **6\. v2.0 Edge-Case Hardening & Production Upgrades (F-01 through F-10)**

The following ten architectural upgrades harden User Stories `US-01` through `US-10` against acoustic drift, Sanskrit prosodic edge cases, and streaming platform delivery requirements:

## **6.1 Acoustic & Multi-Pandit Synchronization Hardening**

| Upgrade ID | Target Story & Module | Root Cause Addressed | Mandatory v2.0 Implementation Rule |
| :---- | :---- | :---- | :---- |
| **F-01: Master-Take Bounded Unison (`±15 ms`)** | `US-05` (`chant_worker.py`) & `US-06` (`vc_worker.py`) | [Vāgdhenu](https://github.com/prathoshap/vagdhenu) lacks an explicit phoneme duration predictor ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)); 5 independent Vāgdhenu seeds drift `80–200 ms` apart mid-hemistich and slur consonant plosives (*k, ṭ, t, p*). | Render **1 Master Vāgdhenu Take** per verse as the syllable-timing anchor, then run 5 stochastic [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc) diffusion passes (`diffusion_steps=40` with distinct diffusion noise seeds) plus a smooth piecewise time-warp clamped strictly within **`±15 ms`**. |
| **F-02: `C#3` (`138.59 Hz`) Prompt Pitch Pre-Normalization** | `US-04` (`voice_forge.py`) | In [Seed-VC inference.py](https://github.com/Plachtaa/seed-vc/blob/main/inference.py), `prompt_condition` retains the reference speaker's original pitch (`F0_ori`). Pitch mismatches between `F0_ori` and Vāgdhenu's `138.59 Hz` tonic cause pitch scoops on the first syllable of a verse. | In `voice_forge.py`, shift every reference WAV via `pyrubberband` (with formant preservation ON) so its median voiced `F0_ori` is centered at **`138.59 Hz` (`C#3`)** ([Benchmark Report](https://github.com/hemanth/sanskrit-tts-web/blob/main/benchmark.md)) before extracting and caching `cached_tensors.pt`. |
| **F-03: `5.5 kHz` Sibilant & Visarga Restoration Crossover** | `US-06` (`vc_worker.py`) | `Seed-VC` downsamples input to `16 kHz` (`8 kHz` Nyquist limit) for `Whisper-base` semantic tokenization, softening high-frequency Sanskrit sibilants (*ś, ṣ, s*), *jihvāmūlīya*, and *visarga* (`ḥ`) aspiration (`5.5–12 kHz`). | Apply a 4th-order Linkwitz-Riley high-pass crossover at `5500 Hz` that blends `30%` of the crisp `5.5–12 kHz` unvoiced fricative band from Vāgdhenu's `BigVGAN-v2` master take into each `44.1 kHz` `Seed-VC` pandit stem. |
| **F-04: Support-Voice *Daṇḍa* Breath Ducking (`-14 dB`)** | `US-07` (`mixer.py`) | Vāgdhenu synthesizes an audible inhalation breath at the mid-verse *daṇḍa* (`E61` in [arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)). Stacking 5 stems in reverb multiplies 5 simultaneous inhalations into an unnatural gasp. | Detect the mid-verse `[breath_start_sample, breath_end_sample]` window in `chant_worker.py`; retain natural breath on Lead Pandit `1` (`pandit_1_mukhya`) while attenuating Support Pandits `2..5` by **`-14 dB`** across the breath window. |

## **6.2 Sanskrit Text, Meter & Liturgical Structure Hardening (US-03)**

57. **F-05: Speaker Connective Isolation (`UVACA_CONNECTIVE`)**:  
    1. **Rule**: Automatically split leading dialogic speaker headers (श्रीभगवानुवाच, भीष्म उवाच, युधिष्ठिर उवाच, हयग्रीव उवाच, पार्वत्युवाच, ईश्वर उवाच, ऋषय ऊचुः) into standalone `UVACA_CONNECTIVE` units before metrical scansion (matching the 1,416 connective units in Table 3 of [arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)). Default all `UVACA_CONNECTIVE` units to **Solo Lead Pandit (`pandit_1_mukhya`)** choreography.  
58. **F-06: 108-Name *Aṣṭottara-Śatanāmāvalī* Breath-Group Packer (`NAMAVALI_108`)**:  
    1. **Rule**: When the input contains short *Nāmāvalī* lines (ॐ विश्वस्मै नमः । ॐ विष्णवे नमः । ...), pack 2 to 4 consecutive *nāmas* into a single `16–24 akṣara` `NAMAVALI_108` unit separated by single *daṇḍas* (।) so the syllable count matches Vāgdhenu's *anuṣṭubh* reference budget without inserting dead padding silence.  
59. **F-07: Odd-Pāda Stotras (3-Pāda *Gāyatrī* & 6-Pāda *Ṣaṭpadī*) and Refrain Caching (`REFRAIN_HOOK`)**:  
    1. **Rule**: Support 1-hemistich (3-pāda *Gāyatrī*), 2-hemistich (4-pāda śloka), and 3-hemistich (6-pāda *Ṣaṭpadī*) units in `stotra_parser.py` without truncating after *pāda* 4\. Automatically tag repeating *pallavi / dhruvapada* refrain stanzas as `REFRAIN_HOOK` so their rendered stems can be cached and chorus-boosted across verses.  
60. **F-08: *Praṇava* (ॐ / ओ३म्) Normalization & Pre-Sandhified (*Saṃhitā*) Detection**:  
    1. **Rule**: Normalize ॐ, ओ३म्, and *pluta* ३ to Vāgdhenu's sustained ಓಂ (`AUM` in `SLP1`, matching [prathoshap/vagdhenu-data](https://huggingface.co/datasets/prathoshap/vagdhenu-data)). Auto-detect pre-sandhified *saṃhitā* verses (via existing *visarga-sibilant* clusters and *avagraha* ऽ) and disable redundant internal *visarga sandhi* on those verses so word-internal visargas (दुःख, अन्तःकरण) are never corrupted.

## **6.3 Liturgical Choreography, Storage & Multi-Platform Export (US-07 – US-09)**

61. **F-09: Dynamic Liturgical Choreography Engine (`choreography_mode`)**:  
    1. **`AUTO_LITURGICAL` (Default)**: Routes `GADYA_PROSE` (*saṅkalpa / nyāsa*) and `UVACA_CONNECTIVE` units to **Solo Lead Pandit (`pandit_1_mukhya` at Center)**, then swells into **Full 5-Pandit Goṣṭhī Unison** on `dhyanam`, `main` *Sahasranāma / Stotra* verses, and `phalashruti`.  
    2. **`ANTIPHONAL_CALL_RESPONSE`**: Alternates Hemistich 1 (*Pandits 1 & 2*) and Hemistich 2 (*Pandits 3, 4 & 5*), uniting all 5 pandits on `REFRAIN_HOOK` and `phalashruti` stanzas.  
    3. **`FULL_UNISON`**: Keeps all K active pandits engaged across every unit.  
62. **F-10: FLAC Stem Compression, Multi-Track Spotify Album Splitter & 1080p YouTube Karaoke Video (`video_exporter.py`)**:  
    1. **Lossless FLAC Intermediate Storage**: Compresses per-pandit intermediate stems to `24-bit FLAC` (`v001_pandit_1.flac`), reducing a 145-verse *Sahasranāma* project footprint from `~3.5 GB` to `~650 MB` and cutting M3 Pro synthesis time to **\~75 minutes** (since Vāgdhenu runs once per verse instead of 5 times).  
    2. **Spotify Multi-Track Album Export (`spotify_split_tracks.zip`)**: Exports both the single stitched master WAV and per-section `-14.0 LUFS` split album tracks (`01_Purvapithika_Dhyanam.wav`, `02_Main_Stotram.wav`, `03_Phalashruti.wav`) with smooth `1.2s` tanpura crossfade tails.  
    3. **Automated 1080p YouTube Karaoke Video (`video_exporter.py`)**: Uses `Pillow` \+ `ffmpeg` (`H.264` \+ `320 kbps AAC`) to render a `1920x1080` (`30 fps`) video displaying synchronized **Devanagari**, **Kannada**, and **IAST** verse cards with active line highlighting.

# **7\. v2.1 Deep DSP Audit Fixes & Unified Override Rules**

Where any earlier clause in Sections 3, 4, or 5 conflicts with Sections 6 and 7, the rules below take strict precedence during implementation:

## **7.1 Resolution of Internal Specification Contradictions (C-01 through C-04)**

| Rule ID | Superseded v1.0 Clause | Authoritative v2.1 Implementation Contract |
| :---- | :---- | :---- |
| **C-01 (US-05 Override)** | `US-05` (`num_takes=K` independent Vāgdhenu seeds per verse) | `chant_worker.py` synthesizes **1 Master Vāgdhenu Take** per verse (`nfe=48` in `preview_dsp`; `nfe=64` in `studio_seedvc`). All 5 pandits derive from this single syllable-timing anchor via 5 stochastic [Plachtaa/seed-vc](https://github.com/Plachtaa/seed-vc) diffusion passes plus a smooth `±15 ms` piecewise time-warp. |
| **C-02 (US-02 Schema Override)** | `US-02` 3-class `unit_type` & minimal `projects`/`verses` columns | `db.py` includes all 6 `unit_type` values (`METRICAL_SLOKA`, `UVACA_CONNECTIVE`, `NAMAVALI_108`, `GADYA_PROSE`, `JAPA_REPEAT`, `REFRAIN_HOOK`), `projects.choreography_mode`, `projects.retain_intermediate_stems`, `projects.split_tracks_zip_path`, `projects.video_mp4_path`, `verses.choreography_override`, `verses.iast_text`, `verses.hemistich_split_sec`, and `verses.breath_windows_sec_json`. |
| **C-03 (US-06/US-07/US-08 File & Route Override)** | Raw `.wav` intermediate stems and missing video route | `vc_worker.py` writes lossless **24-bit FLAC** stems (`v001_pandit_1.flac`), `backend/engine/video_exporter.py` is added to the engine package, and `main.py` exposes `POST /api/projects/{id}/export-video`. |
| **C-04 (US-04 Verification Override)** | `verify_us04_voice_forge.py` checking only `style2.shape` | `verify_us04_voice_forge.py` additionally asserts that every cached persona's `F0_ori` median voiced frequency falls within `138.59 ± 2.0 Hz` (`C#3`) ([Benchmark Report](https://github.com/hemanth/sanskrit-tts-web/blob/main/benchmark.md)). |

## **7.2 Nine Deep DSP, Concurrency & Linguistic Hardening Rules (Flaws 6 through 14\)**

63. **Flaw 6 Fix — Lead-Only Sibilant Restoration (Prevents High-Frequency Comb Filtering)**:  
    1. **Problem**: Blending the `5.5–12 kHz` high-frequency band from the single master take into all 5 time-warped pandit stems causes severe metallic comb filtering when the 5 stems are summed.  
    2. **Rule**: Inject the `5.5–12 kHz` unvoiced fricative/sibilant restoration band **exclusively into the Center Lead Pandit (`pandit_1_mukhya`, which remains at `0.0 ms` time warp)**, and apply a gentle `7.5 kHz` low-pass roll-off to Support Pandits `2..5`.  
64. **Flaw 7 Fix — Mid-Verse *Daṇḍa* Splitting for Long Meters in `Seed-VC` (`hemistich_split_sec`)**:  
    1. **Problem**: [Seed-VC inference.py](https://github.com/Plachtaa/seed-vc/blob/main/inference.py) has a 30-second total context window (15 seconds of reference prompt \+ 15 seconds of source audio). Long meters like *Śārdūlavikrīḍita* and *Sragdharā* last `18–23 seconds` ([arXiv:2608.26146](https://arxiv.org/pdf/2608.26146)) and get sliced mid-vowel at `15.0s`.  
    2. **Rule**: Whenever a master verse exceeds `13.5 seconds`, `vc_worker.py` splits the source audio at `verse.hemistich_split_sec` (the silent mid-verse *daṇḍa* boundary), converts Hemistich 1 and Hemistich 2 independently, and crossfades them across a `30 ms` window at the *daṇḍa*.  
65. **Flaw 8 Fix — Sample-Rate-Independent Breath Coordinates (`breath_windows_sec_json`)**:  
    1. **Problem**: Sample indices recorded at `24 kHz` in `chant_worker.py` become invalid after resampling to `44.1 kHz` (`Seed-VC`) and `48 kHz` (`mixer.py`).  
    2. **Rule**: Store all detected *daṇḍa* inhalation windows in **floating-point seconds (`[[start_sec, end_sec]]`)** with `25 ms` cosine fade handles.  
66. **Flaw 9 Fix — Explicit Rubber Band R3 Formant Preservation Flags (`rbargs`)**:  
    1. **Problem**: Calling `pyrubberband.pitch_shift()` with default flags shifts vocal-tract formants when normalizing reference pitch to `138.59 Hz`.  
    2. **Rule**: Always pass `rbargs=["-3", "-F"]` (Rubber Band R3 finer engine \+ formant preservation) when normalizing `F0_ori` to `138.59 Hz` in `voice_forge.py`.  
67. **Flaw 10 Fix — Global Apple Metal Concurrency Lock (`MPS_LOCK`)**:  
    1. **Problem**: PyTorch `mps` command buffers crash if an admin triggers a voice audition in `/admin/voices` while the background worker is executing a verse forward pass.  
    2. **Rule**: Guard all `torch.device("mps")` forward passes across `chant_worker.py`, `vc_worker.py`, and `voice_forge.py` with a single thread-safe `MPS_LOCK` so interactive UI requests execute cleanly between batch verses.  
68. **Flaw 11 Fix — Solo-to-Chorus Dynamic Staging (Prevents Solo Volume Pumping)**:  
    1. **Problem**: Normalizing each verse independently to `-14.0 LUFS` boosts a 1-pandit `UVACA_CONNECTIVE` (भीष्म उवाच) by `+7 dB`, making 1 solo pandit sound as loud as 5 pandits in unison.  
    2. **Rule**: Calibrate each individual pandit stem to `-20.0 dBFS` active RMS, apply a `-2.5 dB` chorus bus trim when 5 voices are active (so the 5-pandit chorus is naturally `~3.5 dB` fuller than a solo connective), and run `pyloudnorm` (`-14.0 LUFS`) **once on the assembled master track**.  
69. **Flaw 12 Fix — HarfBuzz / `libass` Indic Shaping for `1080p` Karaoke Video (`video_exporter.py`)**:  
    1. **Problem**: Un-shaped `Pillow` text rendering breaks Devanagari `ि` matras and Kannada subscript conjuncts (*ottaksharas*).  
    2. **Rule**: Generate an `.ass` (Advanced SubStation Alpha) subtitle file containing the synchronized **Devanagari**, **Kannada**, and **IAST** lines and render the `1080p` video via `ffmpeg -vf "ass=lyrics.ass"`, leveraging `libass` \+ `HarfBuzz` for native Indic ligature shaping.  
70. **Flaw 13 Fix — Cross-Verse Tonic Drift Correction (`±25 cents` Micro-Tuner)**:  
    1. **Problem**: Flow-matching synthesis can drift `±15–25 cents` around the `138.5913 Hz` (`C#3`) tonic from verse to verse, causing audible beating against a continuous digital tanpura drone over a 38-minute *Sahasranāma*.  
    2. **Rule**: In `chant_worker.py`, measure each master take's median voiced `F0` relative to `138.5913 Hz` and apply a static micro-pitch trim (clamped to `±35 cents`) via `pyrubberband` (`rbargs=["-3", "-F"]`) before voice conversion so every verse stays at `0.0 cents` relative to the continuous tanpura.  
71. **Flaw 14 Fix — Intra-Pāda Space Normalization & Sustained Vowel Audition Gate**:  
    1. **Problem**: As documented in Section 8.3 of [arXiv:2608.26146](https://arxiv.org/pdf/2608.26146), spaces inside a quarter-verse can cause micro-pauses, and conversational `Indic Parler-TTS` prompts can sound slightly nasal when stretched onto long chanted vowels.  
    2. **Rule**: `stotra_parser.py` joins non-*yati* intra-pāda spaces after sandhi resolution so each quarter-verse is synthesized as a continuous breath group, and `seed_default_pandits.py` uses sustained-vowel calibration prompts (ಆ... ಈ... ಊ... ಓಂ...) when generating or auditioning target pandit voices.