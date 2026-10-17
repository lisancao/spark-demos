#!/usr/bin/env python3
"""
Narrative Analyzer — Quality checking for RPG narrative output.

Profiles generated RPG text for: sensory coverage, second-person consistency,
pacing, dialogue quality, and atmosphere density. Ensures the LLM output
meets quality standards before presenting to the player.

Adapted from Writer's Hand analyze_prose.py.
"""

import re
import statistics
from collections import Counter
from typing import Any


# ---------------------------------------------------------------------------
# Sensory keywords (tuned for RPG narrative)
# ---------------------------------------------------------------------------

SENSORY_KEYWORDS = {
    "sight": [
        "light", "dark", "shadow", "bright", "glow", "gleam", "flash",
        "color", "red", "blue", "green", "white", "black", "pale",
        "dim", "shimmer", "glint", "flicker",
        "see", "saw", "watch", "look", "gaze", "glance", "stare",
        "visible", "invisible",
    ],
    "sound": [
        "sound", "noise", "silence", "silent", "quiet", "loud",
        "voice", "whisper", "shout", "scream", "cry", "roar",
        "crack", "snap", "hiss", "rumble", "ring", "creak",
        "hear", "heard", "listen", "echo",
        "clatter", "thud", "boom", "click", "murmur", "hum",
    ],
    "smell": [
        "smell", "scent", "stink", "stench", "odor",
        "reek", "fragrance", "aroma", "musk",
        "sniff", "inhale", "acrid", "pungent",
    ],
    "taste": [
        "taste", "flavor", "bitter", "sweet", "sour", "salt",
        "tongue", "mouth", "swallow", "drink", "eat",
    ],
    "touch": [
        "touch", "feel", "felt", "cold", "warm", "hot", "heat", "chill",
        "rough", "smooth", "soft", "hard", "sharp",
        "wet", "dry", "damp", "slick", "sticky",
        "grip", "grab", "press", "skin", "hand", "finger",
        "weight", "heavy", "pressure",
    ],
}

# RPG-specific quality markers
PLAYER_AGENCY_MARKERS = [
    r"\byou can\b", r"\byou might\b", r"\byou could\b",
    r"\byou notice\b", r"\byou see\b", r"\byou hear\b",
    r"\byou feel\b", r"\byou sense\b",
    r"\bwhat do you do\b", r"\bwhat will you do\b",
    r"\byour move\b", r"\byour choice\b",
]

# Passive/weak constructions to flag
WEAK_CONSTRUCTIONS = [
    (r"\bthere is\b", "there is"),
    (r"\bthere are\b", "there are"),
    (r"\bthere was\b", "there was"),
    (r"\bthere were\b", "there were"),
    (r"\bit seems\b", "it seems"),
    (r"\bit appears\b", "it appears"),
    (r"\byou feel like\b", "you feel like (show, don't tell)"),
    (r"\byou sense that\b", "you sense that (show the sensation)"),
    (r"\bfor some reason\b", "for some reason (vague)"),
    (r"\bsomething about\b", "something about (vague)"),
]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_narrative(text: str, name: str = "scene") -> dict[str, Any]:
    """Run quality analysis on RPG narrative text."""
    words = text.split()
    word_count = len(words)
    text_lower = text.lower()

    if word_count < 10:
        return {"name": name, "error": "Text too short to analyze", "word_count": word_count}

    # --- Sentence analysis ---
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\*])', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    sent_lengths = [len(s.split()) for s in sentences]
    total_sents = len(sent_lengths)

    if total_sents == 0:
        return {"name": name, "error": "No sentences found", "word_count": word_count}

    cv = 0
    if len(sent_lengths) > 1 and statistics.mean(sent_lengths) > 0:
        cv = statistics.stdev(sent_lengths) / statistics.mean(sent_lengths)

    # --- POV consistency (should be second person) ---
    second_person = len(re.findall(r'\byou\b', text_lower))
    first_person = len(re.findall(r'\b(?:i|me|my|mine)\b', text_lower))
    third_person = len(re.findall(r'\b(?:he|she|they|him|her|them|his|hers|their)\b', text_lower))

    pov_ratio = {
        "second_person": second_person,
        "first_person": first_person,
        "third_person": third_person,
    }
    dominant_pov = max(pov_ratio, key=pov_ratio.get)

    # --- Sensory coverage ---
    sensory_counts = {}
    for modality, keywords in SENSORY_KEYWORDS.items():
        count = sum(
            len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower))
            for kw in keywords
        )
        sensory_counts[modality] = count

    total_sensory = sum(sensory_counts.values())
    sensory_per_1k = {
        k: round(v / (word_count / 1000), 2)
        for k, v in sensory_counts.items()
    } if word_count > 0 else {}

    # --- Player agency ---
    agency_count = sum(
        len(re.findall(pattern, text_lower))
        for pattern in PLAYER_AGENCY_MARKERS
    )
    has_action_prompt = bool(re.search(
        r'what (?:do|will) you|your (?:move|choice|turn)',
        text_lower,
    ))

    # --- Weak constructions ---
    weak_hits = []
    for pattern, label in WEAK_CONSTRUCTIONS:
        matches = list(re.finditer(pattern, text_lower))
        if matches:
            weak_hits.append({"pattern": label, "count": len(matches)})

    # --- Dialogue ratio ---
    dialogue_lines = sum(1 for s in sentences if '"' in s or '\u201c' in s)
    dialogue_ratio = dialogue_lines / total_sents if total_sents > 0 else 0

    # --- Build profile ---
    return {
        "name": name,
        "word_count": word_count,
        "sentence_count": total_sents,
        "sentence_length": {
            "mean": round(statistics.mean(sent_lengths), 1),
            "cv": round(cv, 3),
        },
        "pov": {
            "dominant": dominant_pov,
            "counts": pov_ratio,
            "second_person_consistent": dominant_pov == "second_person",
        },
        "sensory": {
            "counts": sensory_counts,
            "per_1k": sensory_per_1k,
            "total_per_1k": round(total_sensory / (word_count / 1000), 2) if word_count > 0 else 0,
            "dominant": max(sensory_counts, key=sensory_counts.get),
            "weakest": min(sensory_counts, key=sensory_counts.get),
            "modalities_used": sum(1 for v in sensory_counts.values() if v > 0),
        },
        "player_agency": {
            "markers": agency_count,
            "has_action_prompt": has_action_prompt,
        },
        "weak_constructions": weak_hits,
        "dialogue_ratio": round(dialogue_ratio, 3),
    }


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def score_narrative(profile: dict) -> dict[str, Any]:
    """Score a narrative profile. Returns scores and issues."""
    if "error" in profile:
        return {"total": 0, "issues": [profile["error"]]}

    scores = {}
    issues = []

    # Sensory coverage (0-25 points).
    modalities = profile["sensory"]["modalities_used"]
    total_sensory = profile["sensory"]["total_per_1k"]
    if modalities >= 4:
        scores["sensory"] = 25
    elif modalities >= 3:
        scores["sensory"] = 20
    elif modalities >= 2:
        scores["sensory"] = 12
    else:
        scores["sensory"] = 5
        issues.append(f"Only {modalities} sense(s) used. Add {profile['sensory']['weakest']} details.")

    if total_sensory < 5:
        issues.append(f"Low sensory density ({total_sensory}/1k). World feels abstract.")

    # POV consistency (0-25 points).
    if profile["pov"]["second_person_consistent"]:
        scores["pov"] = 25
    else:
        scores["pov"] = 10
        issues.append(f"POV inconsistency: dominant is {profile['pov']['dominant']}, expected second_person.")

    # Rhythm variety (0-25 points).
    cv = profile["sentence_length"]["cv"]
    if cv >= 0.5:
        scores["rhythm"] = 25
    elif cv >= 0.3:
        scores["rhythm"] = 18
    else:
        scores["rhythm"] = 8
        issues.append(f"Low rhythm variety (CV={cv:.2f}). Sentences too uniform.")

    # Player agency (0-25 points).
    agency = profile["player_agency"]["markers"]
    has_prompt = profile["player_agency"]["has_action_prompt"]
    if agency >= 3 and has_prompt:
        scores["agency"] = 25
    elif agency >= 2:
        scores["agency"] = 18
    elif agency >= 1 or has_prompt:
        scores["agency"] = 12
    else:
        scores["agency"] = 5
        issues.append("Low player agency. Add 'you' actions and end with a choice prompt.")

    if not has_prompt:
        issues.append("No action prompt at the end. Player needs a clear 'what do you do?' moment.")

    # Weak construction penalty.
    total_weak = sum(h["count"] for h in profile.get("weak_constructions", []))
    if total_weak > 5:
        scores["weak_penalty"] = -5
        issues.append(f"{total_weak} weak constructions ('there is/was', 'it seems', etc.). Tighten prose.")
    else:
        scores["weak_penalty"] = 0

    total = sum(scores.values())
    return {
        "total": max(0, total),
        "max": 100,
        "breakdown": scores,
        "issues": issues,
        "grade": _grade(total),
    }


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(profile: dict, score: dict) -> str:
    """Format analysis + score into a readable report."""
    lines = []
    lines.append(f"## Narrative Quality: {profile.get('name', '?')}")
    lines.append(f"Words: {profile.get('word_count', 0)} | Sentences: {profile.get('sentence_count', 0)}")
    lines.append("")

    # Score.
    lines.append(f"### Score: {score['total']}/{score['max']} ({score['grade']})")
    for k, v in score.get("breakdown", {}).items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    # Issues.
    if score.get("issues"):
        lines.append("### Issues")
        for issue in score["issues"]:
            lines.append(f"  - {issue}")
        lines.append("")

    # Sensory.
    s = profile.get("sensory", {})
    lines.append("### Sensory Coverage")
    for modality in ["sight", "sound", "touch", "smell", "taste"]:
        val = s.get("per_1k", {}).get(modality, 0)
        bar = "#" * int(val * 2)
        flag = " <- WEAK" if val < 1 else ""
        lines.append(f"  {modality:6s}: {val:5.1f}/1k  {bar}{flag}")
    lines.append("")

    # POV.
    pov = profile.get("pov", {})
    lines.append(f"### POV: {pov.get('dominant', '?')} {'(correct)' if pov.get('second_person_consistent') else '(MISMATCH)'}")
    lines.append("")

    # Weak constructions.
    weak = profile.get("weak_constructions", [])
    if weak:
        lines.append("### Weak Constructions")
        for h in weak:
            lines.append(f"  {h['pattern']}: {h['count']}x")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python narrative_analyzer.py <text_file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    from pathlib import Path
    text = filepath.read_text()
    profile = analyze_narrative(text, name=filepath.stem)
    score = score_narrative(profile)
    print(format_report(profile, score))
