"""Narrative Guard — lightweight post-generation validation.

Checks LLM-generated narrative for contradictions against NPC profiles
and world data. Does NOT block output — flags issues for logging or
optional correction. The game should surprise you. It just shouldn't
get the cast wrong.

Design principle: catch contradictions, allow inventions. If the model
adds a detail not in the YAML (a pouch on a belt, a scar), that's fine.
If it contradicts a detail that IS in the YAML (wrong gender, wrong
weapon hand), that's a flag.
"""

import re
from typing import Optional


# Pronoun sets for gender detection.
MALE_PRONOUNS = {"he", "him", "his", "himself"}
FEMALE_PRONOUNS = {"she", "her", "hers", "herself"}


def _infer_gender(appearance: str) -> Optional[str]:
    """Infer gender from appearance text. Returns 'male', 'female', or None."""
    words = set(re.findall(r'\b\w+\b', appearance.lower()))

    female_keywords = {"woman", "she", "her", "hers", "herself", "girl", "lady", "queen", "mistress", "female"}
    male_keywords = {"man", "he", "him", "his", "himself", "boy", "lord", "king", "male"}

    # "her" also appears in female text as possessive ("her knife"), so it's a valid signal.
    # "he" inside "the" or "she" would be caught by word-boundary extraction above.
    f_count = len(words & female_keywords)
    m_count = len(words & male_keywords)

    if f_count > m_count:
        return "female"
    elif m_count > f_count:
        return "male"
    return None


def _extract_pronouns_near_name(text: str, name: str) -> set[str]:
    """Find pronouns used near an NPC name mention.

    Uses sentence-level proximity instead of character windows to avoid
    picking up pronouns from adjacent NPC descriptions.
    """
    text_lower = text.lower()
    name_lower = name.lower()
    pronouns_found = set()

    # Split into sentences, check only sentences that contain this NPC's name.
    sentences = re.split(r'[.!?]+', text_lower)
    for sentence in sentences:
        if name_lower in sentence:
            words = set(re.findall(r'\b\w+\b', sentence))
            pronouns_found.update(words & (MALE_PRONOUNS | FEMALE_PRONOUNS))

    return pronouns_found


def check_narrative(text: str, npcs: list[dict]) -> list[dict]:
    """Check generated narrative against NPC profiles.

    Returns a list of issues found. Each issue is a dict:
        {"type": "gender_mismatch", "npc": "Valdys", "detail": "..."}

    Empty list = no issues detected.
    """
    issues = []

    for npc in npcs:
        name = npc.get("name", "")
        if not name or name.lower() not in text.lower():
            continue

        appearance = npc.get("appearance", "") + " " + npc.get("appearance_brief", "")
        expected_gender = _infer_gender(appearance)

        if not expected_gender:
            # No gender detected in profile — skip pronoun checks.
            # Gender-neutral NPCs or ambiguous profiles are allowed any pronouns.
            continue

        # Check pronouns used near this NPC's name.
        pronouns = _extract_pronouns_near_name(text, name)

        if expected_gender == "female" and pronouns & MALE_PRONOUNS:
            issues.append({
                "type": "gender_mismatch",
                "npc": name,
                "expected": "female",
                "found_pronouns": list(pronouns & MALE_PRONOUNS),
                "detail": f"{name} is female but narrative uses male pronouns: {pronouns & MALE_PRONOUNS}",
            })
        elif expected_gender == "male" and pronouns & FEMALE_PRONOUNS:
            issues.append({
                "type": "gender_mismatch",
                "npc": name,
                "expected": "male",
                "found_pronouns": list(pronouns & FEMALE_PRONOUNS),
                "detail": f"{name} is male but narrative uses female pronouns: {pronouns & FEMALE_PRONOUNS}",
            })

    return issues


def format_issues(issues: list[dict]) -> str:
    """Format issues for display/logging."""
    if not issues:
        return ""
    lines = ["[Narrative Guard]"]
    for issue in issues:
        lines.append(f"  ! {issue['detail']}")
    return "\n".join(lines)
