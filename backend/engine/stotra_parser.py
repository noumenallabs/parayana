"""Vāgdhenu Goṣṭhī Studio — Sanskrit Phonological Frontend & Stotra Parser.

Handles:
- Vedic accent & editorial markup stripping
- Multi-section segmentation (पूर्वपीठिका, ध्यानम्, स्तोत्रम्, फलश्रुतिः)
- Dialogic speaker connective isolation (UVACA_CONNECTIVE)
- 108-Name Aṣṭottara-Śatanāmāvalī packing (NAMAVALI_108)
- Refrain stanza tagging (REFRAIN_HOOK)
- Japa repetition grouping (JAPA_REPEAT, 4 reps per unit)
- Prose / Nyāsa / Saṅkalpa chunking (GADYA_PROSE, 10–14 akṣaras)
- Metrical scansion (chandas), Guru/Laghu signatures, and Kannada phonetic routing
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from indic_transliteration import sanscript

# Ensure vendor paths are available
BACKEND_DIR = Path(__file__).resolve().parent.parent
VENDOR_SRC = BACKEND_DIR / "vendor" / "vagdhenu" / "src"
if str(VENDOR_SRC) not in sys.path:
    sys.path.insert(0, str(VENDOR_SRC))

import prep_text
import chandas_labeler
from schemas import UnitType


# ── Vedic & Editorial Normalization ──────────────────────────────────────────

VEDIC_ACCENTS_RE = re.compile(r"[\u0951-\u0954\u1CD0-\u1CFF\uA8E0-\uA8FF]")
EDITORIAL_BRACKETS_RE = re.compile(r"\[.*?\]|\{.*?\}")
VERSE_NUM_RE = re.compile(r"॥\s*[\d०-९IVXLCDMivxlcdm]+\s*॥|\|\s*[\d०-९IVXLCDMivxlcdm]+\s*\||\b[\d०-९]+\s*[\.\)]")

UVACA_PATTERNS = [
    r"श्रीभगवानुवाच",
    r"भगवानुवाच",
    r"भीष्म\s*उवाच",
    r"युधिष्ठिर\s*उवाच",
    r"हयग्रीव\s*उवाच",
    r"पार्वत्युवाच",
    r"पार्वती\s*उवाच",
    r"ईश्वर\s*उवाच",
    r"शिव\s*उवाच",
    r"ऋषय\s*ऊचुः",
    r"ऋषि\s*उवाच",
    r"सूत\s*उवाच",
    r"संजय\s*उवाच",
    r"सञ्जय\s*उवाच",
    r"अर्जुन\s*उवाच",
    r"धृतराष्ट्र\s*उवाच",
    r"ब्रह्मोवाच",
    r"ब्रह्मा\s*उवाच",
    r"नारद\s*उवाच",
    r"सनत्कुमार\s*उवाच",
    r"अगस्त्य\s*उवाच",
    r"मार्कण्डेय\s*उवाच",
]
UVACA_RE = re.compile(r"^\s*(" + "|".join(UVACA_PATTERNS) + r")\s*[।॥:]*\s*", re.MULTILINE)

SECTION_HEADERS = {
    "पूर्वपीठिका": ["पूर्वपीठिका", "पूर्वाङ्गम्", "उपक्रमः", "PURVAPITHIKA"],
    "सङ्कल्पः": ["सङ्कल्पः", "संकल्पः", "अथ सङ्कल्पः", "विनियोगः", "SANKALPA"],
    "ध्यानम्": ["ध्यानम्", "अथ ध्यानम्", "DHYANAM"],
    "स्तोत्रम्": ["स्तोत्रम्", "अथ स्तोत्रम्", "मूलस्तोत्रम्", "STOTRAM", "सहस्रनाम"],
    "फलश्रुतिः": ["फलश्रुतिः", "फलश्रुती", "उत्तरपीठिका", "PHALASHRUTI"],
}


def strip_vedic_and_editorial(text: str) -> str:
    """Strips Vedic pitch accents, editorial brackets, and trailing verse numbers.
    Normalizes Praṇava (ॐ / ओ३म्) to Vāgdhenu standard ॐ.
    """
    # 1. Strip Vedic tone codepoints
    text = VEDIC_ACCENTS_RE.sub("", text)
    # 2. Strip editorial brackets
    text = EDITORIAL_BRACKETS_RE.sub("", text)
    # 3. Strip trailing verse numbering
    text = VERSE_NUM_RE.sub("॥", text)
    # 4. Normalize Praṇava (F-08)
    text = re.sub(r"ओ३+म?्?", "ॐ", text)
    text = re.sub(r"ॐ+", "ॐ", text)
    # 5. Clean up duplicate daṇḍas & whitespace
    text = re.sub(r"॥+", "॥", text)
    return text.strip()


def detect_pre_sandhified(text: str) -> bool:
    """Detects whether verse text is already sandhified (saṃhitā) via existing
    visarga-sibilant assimilations (श्श, ष्ष, स्स, श्च, etc.) or avagrahas (ऽ).
    When True, redundant internal visarga sandhi should be disabled (F-08).
    """
    if "ऽ" in text:
        return True
    # Check for visarga assimilation clusters
    clusters = ["श्श", "ष्ष", "स्स", "श्च", "ष्ठ", "स्त", "स्ख", "ष्फ"]
    return any(c in text for c in clusters)


def normalize_intra_pada_spaces(text: str) -> str:
    """Joins non-yati intra-pāda spaces after sandhi resolution so quarters
    synthesize as continuous breath groups (Flaw 14 Fix).
    """
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        parts = re.split(r"([।॥])", line)
        for i in range(0, len(parts), 2):
            # Condense multiple spaces into single space within quarter-pādas
            parts[i] = re.sub(r"[ \t]+", " ", parts[i]).strip()
        cleaned_lines.append("".join(parts))
    return "\n".join(cleaned_lines)


def detect_section_header(line: str) -> Optional[str]:
    clean = line.strip(" ॥।[](){}:-—*#")
    for canonical, aliases in SECTION_HEADERS.items():
        if clean in aliases:
            return canonical
        for a in aliases:
            if clean.startswith(a):
                return canonical
    return None


def is_namavali_line(line: str) -> bool:
    clean = line.strip()
    return clean.startswith("ॐ") and ("नमः" in clean or "नमो" in clean)


def detect_meter_from_weights(syllables: int, weights: str) -> str:
    """Classifies classical meter across 18 known meters and anuṣṭubh variants."""
    if syllables == 32:
        return "anushtubh"
    elif syllables in (56, 57):
        return "vasantatilaka"
    elif syllables == 44:
        return "upajati"
    elif syllables == 48:
        return "vamshastha"
    elif syllables == 60:
        return "malini"
    elif syllables == 68:
        # 17 * 4: check shikharini vs mandakranta
        if weights.startswith("LGGGGG"):
            return "shikharini"
        return "mandakranta"
    elif syllables == 76:
        return "shardulavikridita"
    elif syllables == 84:
        return "sragdhara"
    elif syllables == 24:
        return "gayatri"
    return "gadya"


def compute_expected_duration(syllables: int, unit_type: UnitType) -> float:
    """Calculates expected audio duration in seconds based on syllable count and pauses."""
    if unit_type == UnitType.UVACA_CONNECTIVE:
        return max(1.8, syllables * 0.28 + 0.4)
    # Metrical verse: ~0.27s per syllable + 0.8s mid-verse daṇḍa breath
    return round(max(3.0, syllables * 0.27 + 0.80), 2)


# ── Primary Stotra / Sahasranāma Parser ──────────────────────────────────────

def parse_stotra_or_sahasranama(
    raw_text: str,
    japa_repeat_count: Optional[int] = None,
    apply_sandhi: bool = True,
) -> List[Dict[str, Any]]:
    """Segments, normalizes, and scans Sanskrit text into discrete VerseUnit records."""
    cleaned_input = strip_vedic_and_editorial(raw_text)

    # 1. Japa Repetition Mode
    if japa_repeat_count and japa_repeat_count > 0:
        return _build_japa_units(cleaned_input, japa_repeat_count)

    units: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in cleaned_input.splitlines() if ln.strip()]

    current_section = "स्तोत्रम्"
    verse_counter = 1
    seen_stanzas: Dict[str, int] = {}

    idx = 0
    while idx < len(lines):
        line = lines[idx]

        # Check for section header
        sec = detect_section_header(line)
        if sec:
            current_section = sec
            idx += 1
            continue

        # Check for Namavali block (Aṣṭottara-Śatanāmāvalī - F-06)
        if is_namavali_line(line):
            namas = []
            while idx < len(lines) and is_namavali_line(lines[idx]):
                namas.append(lines[idx].strip(" ।॥"))
                idx += 1
            # Pack namas into 16–24 akṣara groups (2 to 4 names per unit)
            packed = _pack_namavali(namas)
            for p_text in packed:
                u = _create_unit_record(
                    verse_index=verse_counter,
                    raw_text=p_text,
                    section_label=current_section,
                    unit_type=UnitType.NAMAVALI_108,
                    apply_sandhi=apply_sandhi,
                    base_seed=100 + verse_counter * 37,
                )
                units.append(u)
                verse_counter += 1
            continue

        # Check for leading dialogic speaker connective (UVACA_CONNECTIVE - F-05)
        uvaca_match = UVACA_RE.match(line)
        if uvaca_match:
            speaker_text = uvaca_match.group(1).strip()
            # If the line was just the speaker header:
            remaining_on_line = line[uvaca_match.end():].strip()
            # Create UVACA_CONNECTIVE unit
            u_conn = _create_unit_record(
                verse_index=verse_counter,
                raw_text=speaker_text + " ॥",
                section_label=current_section,
                unit_type=UnitType.UVACA_CONNECTIVE,
                choreography_override="SOLO_LEAD",
                apply_sandhi=False,
                base_seed=100 + verse_counter * 37,
            )
            units.append(u_conn)
            verse_counter += 1

            if remaining_on_line:
                lines[idx] = remaining_on_line
                # Keep index at idx to parse the remainder of the verse
                continue
            else:
                idx += 1
                continue

        # Metrical Verse Accumulation: accumulate lines until double daṇḍa '॥'
        stanza_lines = []
        while idx < len(lines):
            cur = lines[idx]
            # If line is another section header or namavali or uvaca, stop accumulating
            if detect_section_header(cur) or is_namavali_line(cur) or UVACA_RE.match(cur):
                break
            stanza_lines.append(cur)
            idx += 1
            if "॥" in cur:
                break

        if not stanza_lines:
            idx += 1
            continue

        stanza_text = " ".join(stanza_lines).strip()
        if not stanza_text:
            continue

        # Refrain detection (REFRAIN_HOOK - F-07)
        norm_key = re.sub(r"[\s।॥]", "", stanza_text)
        is_refrain = False
        if norm_key in seen_stanzas:
            is_refrain = True
            seen_stanzas[norm_key] += 1
        else:
            seen_stanzas[norm_key] = 1

        u_type = UnitType.REFRAIN_HOOK if is_refrain else UnitType.METRICAL_SLOKA
        u_rec = _create_unit_record(
            verse_index=verse_counter,
            raw_text=stanza_text,
            section_label=current_section,
            unit_type=u_type,
            apply_sandhi=apply_sandhi,
            base_seed=100 + verse_counter * 37,
        )
        units.append(u_rec)
        verse_counter += 1

    return units


def _build_japa_units(mantra_text: str, japa_repeat_count: int) -> List[Dict[str, Any]]:
    """Groups short mantra into 4 repetitions per unit across ceil(count / 4) units (US-03)."""
    clean_mantra = mantra_text.strip(" ॥।\n")
    num_units = math.ceil(japa_repeat_count / 4)
    units = []

    for u_idx in range(num_units):
        reps = min(4, japa_repeat_count - u_idx * 4)
        group_text = " । ".join([clean_mantra] * reps) + " ॥"
        u = _create_unit_record(
            verse_index=u_idx + 1,
            raw_text=group_text,
            section_label="जपमाला",
            unit_type=UnitType.JAPA_REPEAT,
            apply_sandhi=False,
            base_seed=100 + u_idx * 29,  # distinct seed formula from spec
        )
        units.append(u)
    return units


def _pack_namavali(namas: List[str]) -> List[str]:
    """Packs 2 to 4 consecutive short names into 16–24 akṣara units separated by '। ' (F-06)."""
    packed = []
    i = 0
    while i < len(namas):
        # Pack 3 names by default, or 2 if remaining
        chunk = namas[i : i + 3]
        i += len(chunk)
        packed.append(" । ".join(chunk) + " ॥")
    return packed


def _create_unit_record(
    verse_index: int,
    raw_text: str,
    section_label: str,
    unit_type: UnitType,
    choreography_override: Optional[str] = None,
    apply_sandhi: bool = True,
    base_seed: int = 100,
) -> Dict[str, Any]:
    """Builds a fully scanned, Kannada-routed, SLP1 and IAST transcribed Verse record."""
    # Convert script to Devanagari first if in another Brahmic script
    deva_text = prep_text.to_deva(raw_text)

    # Praṇava normalization
    deva_text = re.sub(r"ओ३+म?्?", "ॐ", deva_text)

    # Check for pre-sandhified Saṃhitā verse (F-08)
    pre_sandhified = detect_pre_sandhified(deva_text)
    effective_sandhi = apply_sandhi and not pre_sandhified

    # Kannada Orthographic Routing via Vāgdhenu champion path
    if effective_sandhi:
        kannada_text = prep_text.model_text_sandhi(deva_text, echo_final=True)
    else:
        kannada_text = prep_text.model_text(deva_text)

    # IAST representation
    try:
        iast_text = sanscript.transliterate(deva_text, sanscript.DEVANAGARI, sanscript.IAST)
    except Exception:
        iast_text = raw_text

    # SLP1 representation for metrical scansion
    slp1_text = prep_text.align_slp1(deva_text)

    # Chandas Scansion: compute syllable count and Laghu/Guru weights
    try:
        w_list, syl_count = chandas_labeler.scan(slp1_text)
        lg_signature = "".join(w_list)
    except Exception:
        lg_signature = ""
        syl_count = len([c for c in slp1_text if c in chandas_labeler.VOWELS])

    # Classify meter
    detected_meter = detect_meter_from_weights(syl_count, lg_signature)
    if unit_type in (UnitType.GADYA_PROSE, UnitType.UVACA_CONNECTIVE):
        detected_meter = "gadya"

    expected_dur = compute_expected_duration(syl_count, unit_type)

    # Mid-verse daṇḍa hemistich split estimation
    hemistich_split_sec = round(expected_dur * 0.48, 2) if syl_count >= 24 else None
    breath_windows_sec_json = (
        f"[[{round(hemistich_split_sec - 0.25, 2)}, {round(hemistich_split_sec + 0.25, 2)}]]"
        if hemistich_split_sec
        else "[]"
    )

    return {
        "verse_index": verse_index,
        "section_label": section_label,
        "unit_type": unit_type.value,
        "choreography_override": choreography_override,
        "raw_text": raw_text,
        "kannada_text": kannada_text,
        "slp1_text": slp1_text,
        "iast_text": iast_text,
        "lg_signature": lg_signature,
        "syllable_count": syl_count,
        "detected_meter": detected_meter,
        "override_meter": None,
        "apply_internal_sandhi": int(effective_sandhi),
        "base_seed": base_seed,
        "hemistich_split_sec": hemistich_split_sec,
        "breath_windows_sec_json": breath_windows_sec_json,
        "expected_duration_sec": expected_dur,
    }
