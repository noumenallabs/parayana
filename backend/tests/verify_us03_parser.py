"""Verification suite for US-03:
Multi-Verse Sahasranāma, Prose (Gadya) & Japa Mantra Parser.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ENGINE_DIR = BACKEND_DIR / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from engine.stotra_parser import (
    strip_vedic_and_editorial,
    parse_stotra_or_sahasranama,
)
from schemas import UnitType


def verify_us03() -> None:
    print("--- Verifying US-03: Sanskrit Phonological Frontend & Stotra Parser ---")

    # 1. Vedic tone marks and verse numbers strip cleanly
    vedic_sample = "अ॒ग्निमी॑ळे पु॒रोहि॑तं य॒ज्ञस्य॑ दे॒वमृ॒त्विज॑म् [ऋग्वेद १.१.१] ॥ १ ॥"
    stripped = strip_vedic_and_editorial(vedic_sample)
    # Ensure all Vedic accents (\u0951-\u0954\u1CD0-\u1CFF\uA8E0-\uA8FF) are gone
    assert not re.search(r"[\u0951-\u0954\u1CD0-\u1CFF\uA8E0-\uA8FF]", stripped), (
        "Vedic accents were not stripped"
    )
    # Ensure editorial brackets [ ... ] are gone
    assert "[" not in stripped and "]" not in stripped, "Editorial brackets were not stripped"
    # Ensure verse number ॥ १ ॥ is replaced cleanly by ॥
    assert "॥ १ ॥" not in stripped and "१" not in stripped, "Verse number was not stripped"
    assert stripped.endswith("॥"), f"Stripped text should end in daṇḍa: {stripped}"
    print("Vedic accent and editorial stripping verified.")

    # 2. Scans वसुदेवसुतं देवं... as anuṣṭubh (32 syllables)
    verse_anushtubh = (
        "वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।\n"
        "देवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥"
    )
    units_anu = parse_stotra_or_sahasranama(verse_anushtubh)
    assert len(units_anu) == 1, f"Expected 1 unit, got {len(units_anu)}"
    u_anu = units_anu[0]
    assert u_anu["syllable_count"] == 32, (
        f"Expected 32 syllables for anuṣṭubh, got {u_anu['syllable_count']}"
    )
    assert u_anu["detected_meter"] == "anushtubh", (
        f"Expected 'anushtubh', got '{u_anu['detected_meter']}'"
    )
    print(f"Anuṣṭubh verified: 32 syllables, meter '{u_anu['detected_meter']}'.")

    # 3. Scans नारायणाय परिपूर्णगुणार्णवाय... as vasantatilaka (56 syllables)
    verse_vasanta = (
        "नारायणाय परिपूर्णगुणार्णवाय विश्वोदयस्थितिलयोन्नियतिप्रदाय ।\n"
        "ज्ञानप्रदाय विबुधासुरसौख्यदुःखसत्कारणाय वितताय नमो नमस्ते ॥"
    )
    units_vasanta = parse_stotra_or_sahasranama(verse_vasanta)
    assert len(units_vasanta) == 1, f"Expected 1 unit, got {len(units_vasanta)}"
    u_vas = units_vasanta[0]
    assert u_vas["syllable_count"] in (56, 57), (
        f"Expected 56/57 syllables for vasantatilakā, got {u_vas['syllable_count']}"
    )
    assert u_vas["detected_meter"] == "vasantatilaka", (
        f"Expected 'vasantatilaka', got '{u_vas['detected_meter']}'"
    )
    print(f"Vasantatilakā verified: {u_vas['syllable_count']} syllables, meter '{u_vas['detected_meter']}'.")

    # 4. Assert kannada_text characters are in Kannada Unicode range \u0C80–\u0CFF (plus whitespace/punct)
    kannada_sample = u_anu["kannada_text"]
    assert kannada_sample, "kannada_text must not be empty"
    for ch in kannada_sample:
        if ch in " \t\n।॥":
            continue
        code = ord(ch)
        assert 0x0C80 <= code <= 0x0CFF, (
            f"Character '{ch}' (U+{code:04X}) is outside Kannada Unicode range 0C80–0CFF"
        )
    print("Kannada orthographic phonetic routing verified.")

    # 5. Japa Repetition Mode: count=108 yields 27 units with distinct seeds
    japa_text = "ॐ नमो नारायणाय"
    japa_units = parse_stotra_or_sahasranama(japa_text, japa_repeat_count=108)
    assert len(japa_units) == 27, f"Expected 27 units for 108 japa, got {len(japa_units)}"
    seeds = [u["base_seed"] for u in japa_units]
    assert len(set(seeds)) == 27, "Japa units must have 27 distinct base seeds"
    assert all(u["unit_type"] == UnitType.JAPA_REPEAT.value for u in japa_units), (
        "All units must be JAPA_REPEAT"
    )
    print(f"Japa repetition mode verified: 108 reps -> {len(japa_units)} units with 27 distinct seeds.")

    # 6. Speaker Connective (UVACA_CONNECTIVE - F-05)
    dialogue_text = "श्रीभगवानुवाach ।\nकर्मण्येवाधिकारस्ते मा फलेषु कदाचन ॥"
    dialogue_units = parse_stotra_or_sahasranama("श्रीभगवानुवाच ।\nकर्मण्येवाधिकारस्ते मा फलेषु कदाचन ॥")
    assert len(dialogue_units) == 2, f"Expected 2 units (connective + verse), got {len(dialogue_units)}"
    assert dialogue_units[0]["unit_type"] == UnitType.UVACA_CONNECTIVE.value
    assert dialogue_units[0]["choreography_override"] == "SOLO_LEAD"
    print("Speaker connective (UVACA_CONNECTIVE) isolation verified.")

    print("VERIFY_PASS: US-03")


if __name__ == "__main__":
    verify_us03()
