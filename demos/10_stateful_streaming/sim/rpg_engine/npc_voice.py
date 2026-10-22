#!/usr/bin/env python3
"""
NPC Voice — Character voice profiles and consistency checking for RPG NPCs.

Each NPC has a voice profile: speech patterns, vocabulary tendencies,
sentence structure preferences. Generated dialogue is checked against
these profiles to prevent voice bleed between characters.

Adapted from Writer's Hand voice_checker.py.
"""

import re
from collections import Counter, defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Voice profile definition
# ---------------------------------------------------------------------------

# Pre-built voice archetypes that can be referenced in NPC definitions.
VOICE_ARCHETYPES = {
    "soldier": {
        "sentence_style": "short, clipped",
        "vocabulary": "military, practical, direct",
        "contractions": "frequent",
        "formality": "low to medium",
        "speech_habits": ["drops subjects ('Seen worse.')", "imperative mood", "minimal hedging"],
        "avoids": ["flowery language", "long explanations", "emotional vocabulary"],
    },
    "scholar": {
        "sentence_style": "complex, subordinate clauses",
        "vocabulary": "educated, precise, sometimes archaic",
        "contractions": "rare",
        "formality": "high",
        "speech_habits": ["qualifies statements", "references knowledge", "asks rhetorical questions"],
        "avoids": ["slang", "crude language", "oversimplification"],
    },
    "merchant": {
        "sentence_style": "varied, persuasive",
        "vocabulary": "commercial, flattering, calculating",
        "contractions": "moderate",
        "formality": "medium — adjusts to customer",
        "speech_habits": ["values and prices things", "comparative language", "friendly but watchful"],
        "avoids": ["giving things away", "committing to absolutes", "revealing margins"],
    },
    "rogue": {
        "sentence_style": "quick, deflective",
        "vocabulary": "street-smart, euphemistic, sarcastic",
        "contractions": "heavy",
        "formality": "low",
        "speech_habits": ["redirects questions", "nicknames for people", "dark humor"],
        "avoids": ["earnest emotion", "formal titles", "long speeches"],
    },
    "noble": {
        "sentence_style": "measured, authoritative",
        "vocabulary": "formal, politically aware, duty-oriented",
        "contractions": "rare",
        "formality": "high",
        "speech_habits": ["speaks in we/our", "references duty/honor", "careful word choice"],
        "avoids": ["slang", "admitting uncertainty publicly", "casual register"],
    },
    "healer": {
        "sentence_style": "calm, reassuring",
        "vocabulary": "medical-adjacent, gentle, practical",
        "contractions": "moderate",
        "formality": "medium",
        "speech_habits": ["asks about symptoms/feelings", "gives instructions gently", "steady tone"],
        "avoids": ["panic language", "blame", "false promises"],
    },
    "mystic": {
        "sentence_style": "elliptical, suggestive",
        "vocabulary": "symbolic, layered, ambiguous",
        "contractions": "rare",
        "formality": "varies — sometimes very high, sometimes folk-simple",
        "speech_habits": ["speaks in riddles or metaphor", "references unseen forces", "comfortable with silence"],
        "avoids": ["direct answers", "mundane concerns", "modern register"],
    },
    "innkeeper": {
        "sentence_style": "warm, practical",
        "vocabulary": "domestic, hospitable, local gossip",
        "contractions": "frequent",
        "formality": "low",
        "speech_habits": ["offers food/drink", "knows everyone's business", "storyteller"],
        "avoids": ["taking sides publicly", "formal register", "violence talk"],
    },
}


# ---------------------------------------------------------------------------
# Voice profiling (analysis of generated dialogue)
# ---------------------------------------------------------------------------

def profile_dialogue(dialogues: list[str]) -> dict[str, Any]:
    """Build a voice profile from a list of dialogue strings.

    Same analysis as Writer's Hand voice_checker, adapted for RPG context.
    """
    if not dialogues:
        return {"error": "No dialogue to profile"}

    all_words = []
    sentence_lengths = []
    starters = []
    questions = 0
    commands = 0
    fragments = 0
    contractions = 0
    total_sentences = 0

    contraction_pattern = re.compile(r"\b\w+['']\w+\b")

    for dialogue in dialogues:
        words = re.findall(r"\b[\w']+\b", dialogue.lower())
        all_words.extend(words)

        sentences = re.split(r'[.!?]+', dialogue)
        sentences = [s.strip() for s in sentences if s.strip()]

        for sent in sentences:
            total_sentences += 1
            sent_words = re.findall(r'\b\w+\b', sent)
            sentence_lengths.append(len(sent_words))
            if sent_words:
                starters.append(sent_words[0].lower())
            if len(sent_words) < 4:
                fragments += 1

        questions += dialogue.count("?")

        if re.match(r'^[A-Z][a-z]+\s', dialogue) and not dialogue.endswith("?"):
            first_word = dialogue.split()[0].lower()
            if first_word in {"stop", "come", "go", "look", "tell", "give", "take",
                              "hold", "sit", "stand", "wait", "listen", "shut",
                              "don't", "let", "keep", "move", "run", "watch",
                              "leave", "stay", "put", "get", "use", "try",
                              "bring", "find", "follow", "help", "show"}:
                commands += 1

        contractions += len(contraction_pattern.findall(dialogue))

    word_counter = Counter(all_words)
    total_words = len(all_words)
    unique_words = len(word_counter)

    avg_sentence_length = sum(sentence_lengths) / max(len(sentence_lengths), 1)

    function_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "that", "this", "it", "i", "you", "he",
        "she", "we", "they", "my", "your", "his", "her", "our", "their",
        "me", "him", "us", "them", "if", "so", "as", "up", "not",
    }
    content_words = Counter({
        w: c for w, c in word_counter.items()
        if w not in function_words and len(w) > 2
    })

    return {
        "total_lines": len(dialogues),
        "total_words": total_words,
        "unique_words": unique_words,
        "vocab_richness": unique_words / max(total_words, 1),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "fragment_pct": round(fragments / max(total_sentences, 1) * 100, 1),
        "question_rate": round(questions / max(len(dialogues), 1) * 100, 1),
        "command_rate": round(commands / max(len(dialogues), 1) * 100, 1),
        "contraction_rate": round(contractions / max(total_words, 1) * 1000, 1),
        "top_starters": Counter(starters).most_common(5),
        "top_words": content_words.most_common(15),
    }


# ---------------------------------------------------------------------------
# Voice consistency checking
# ---------------------------------------------------------------------------

def check_voice_consistency(dialogue: str, voice_profile: dict) -> list[dict]:
    """Check a piece of dialogue against an NPC's voice profile.

    Returns a list of findings (violations).
    """
    findings = []

    if not voice_profile:
        return findings

    text_lower = dialogue.lower()
    words = re.findall(r"\b[\w']+\b", text_lower)

    # Check formality level.
    formality = voice_profile.get("formality", "").lower()
    if "high" in formality:
        # High formality NPCs shouldn't use heavy contractions.
        contraction_count = len(re.findall(r"\b\w+['']\w+\b", dialogue))
        if contraction_count > 2:
            findings.append({
                "type": "formality_mismatch",
                "severity": "medium",
                "detail": f"High-formality NPC uses {contraction_count} contractions.",
            })
    elif "low" in formality:
        # Low formality NPCs shouldn't use overly formal constructions.
        formal_markers = ["furthermore", "moreover", "nevertheless", "henceforth",
                          "whereupon", "inasmuch", "notwithstanding"]
        found = [w for w in formal_markers if w in text_lower]
        if found:
            findings.append({
                "type": "formality_mismatch",
                "severity": "medium",
                "detail": f"Low-formality NPC uses formal words: {', '.join(found)}",
            })

    # Check avoids list.
    avoids = voice_profile.get("avoids", [])
    for avoid in avoids:
        avoid_lower = avoid.lower()
        # Simple keyword check — could be smarter with semantic matching.
        if any(keyword in text_lower for keyword in avoid_lower.split()):
            findings.append({
                "type": "voice_violation",
                "severity": "low",
                "detail": f"NPC should avoid '{avoid}' but dialogue may contain it.",
            })

    # Check sentence style.
    sentence_style = voice_profile.get("sentence_style", "").lower()
    sentences = re.split(r'[.!?]+', dialogue)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    if "short" in sentence_style or "clipped" in sentence_style:
        if avg_len > 15:
            findings.append({
                "type": "style_mismatch",
                "severity": "medium",
                "detail": f"NPC should speak in short sentences but avg is {avg_len:.0f} words.",
            })
    elif "complex" in sentence_style:
        if avg_len < 8 and len(sentences) > 2:
            findings.append({
                "type": "style_mismatch",
                "severity": "low",
                "detail": f"NPC should speak in complex sentences but avg is only {avg_len:.0f} words.",
            })

    return findings


def detect_voice_bleed(npc_dialogues: dict[str, list[str]]) -> list[dict]:
    """Compare dialogue across NPCs and flag potential voice bleed.

    npc_dialogues: {npc_id: [list of dialogue strings]}
    """
    profiles = {}
    for npc_id, dialogues in npc_dialogues.items():
        if dialogues:
            profiles[npc_id] = profile_dialogue(dialogues)

    findings = []
    npc_ids = [n for n in profiles if "error" not in profiles[n]]

    if len(npc_ids) < 2:
        return findings

    for i, npc_a in enumerate(npc_ids):
        for npc_b in npc_ids[i+1:]:
            pa = profiles[npc_a]
            pb = profiles[npc_b]

            if pa["total_words"] < 20 or pb["total_words"] < 20:
                continue

            signals = []

            # Sentence length similarity.
            len_diff = abs(pa["avg_sentence_length"] - pb["avg_sentence_length"])
            if len_diff < 1.0:
                signals.append(
                    f"Nearly identical sentence length ({pa['avg_sentence_length']} vs {pb['avg_sentence_length']})"
                )

            # Shared distinctive vocabulary.
            words_a = set(w for w, _ in pa["top_words"])
            words_b = set(w for w, _ in pb["top_words"])
            common = {"just", "know", "don't", "what", "like", "got", "get",
                       "one", "would", "could", "there", "here", "back", "all"}
            shared = (words_a & words_b) - common
            if shared:
                signals.append(f"Shared distinctive vocabulary: {', '.join(sorted(shared))}")

            # Contraction rate similarity.
            contr_diff = abs(pa["contraction_rate"] - pb["contraction_rate"])
            if contr_diff < 5 and (pa["contraction_rate"] > 10 or pb["contraction_rate"] > 10):
                signals.append(
                    f"Similar contraction rates ({pa['contraction_rate']} vs {pb['contraction_rate']} per 1k)"
                )

            if signals:
                severity = "high" if len(signals) >= 3 else "medium" if len(signals) >= 2 else "low"
                findings.append({
                    "npcs": (npc_a, npc_b),
                    "signals": signals,
                    "severity": severity,
                })

    return findings


# ---------------------------------------------------------------------------
# Dialogue generation context
# ---------------------------------------------------------------------------

def build_voice_instructions(npc: dict) -> str:
    """Build voice instructions for an NPC to include in generation prompts.

    Takes an NPC dict (from npcs.yaml) and produces a concise voice guide.
    """
    lines = []
    voice = npc.get("voice_profile", {})
    name = npc.get("name", "this NPC")

    if not voice:
        # Check for archetype reference.
        archetype = npc.get("voice_archetype", "")
        if archetype and archetype in VOICE_ARCHETYPES:
            voice = VOICE_ARCHETYPES[archetype]
        else:
            return f"No voice profile defined for {name}. Use neutral, setting-appropriate speech."

    lines.append(f"VOICE GUIDE: {name.upper()}")
    lines.append("")

    if voice.get("sentence_style"):
        lines.append(f"Sentence style: {voice['sentence_style']}")
    if voice.get("vocabulary"):
        lines.append(f"Vocabulary: {voice['vocabulary']}")
    if voice.get("contractions"):
        lines.append(f"Contractions: {voice['contractions']}")
    if voice.get("formality"):
        lines.append(f"Formality: {voice['formality']}")

    habits = voice.get("speech_habits", [])
    if habits:
        lines.append(f"\nSpeech habits:")
        for h in habits:
            lines.append(f"  - {h}")

    avoids = voice.get("avoids", [])
    if avoids:
        lines.append(f"\n{name} DOES NOT:")
        for a in avoids:
            lines.append(f"  - {a}")

    # Add example lines if provided.
    examples = voice.get("example_lines", [])
    if examples:
        lines.append(f"\nExample lines (for tone/rhythm reference):")
        for ex in examples[:5]:
            lines.append(f'  "{ex}"')

    return "\n".join(lines)


def format_voice_report(npc_dialogues: dict[str, list[str]],
                        npc_profiles: dict[str, dict] = None) -> str:
    """Format a voice consistency report across NPCs."""
    lines = []
    lines.append("## NPC Voice Consistency Report")
    lines.append("")

    # Profile each NPC's generated dialogue.
    profiles = {}
    for npc_id, dialogues in npc_dialogues.items():
        if dialogues:
            profiles[npc_id] = profile_dialogue(dialogues)

    # Per-NPC stats.
    for npc_id, profile in profiles.items():
        if "error" in profile:
            lines.append(f"**{npc_id}:** {profile['error']}")
            continue
        lines.append(f"**{npc_id}** ({profile['total_lines']} lines, {profile['total_words']} words)")
        lines.append(f"  Avg sentence: {profile['avg_sentence_length']} words")
        lines.append(f"  Fragments: {profile['fragment_pct']}% | Questions: {profile['question_rate']}% | Commands: {profile['command_rate']}%")
        lines.append(f"  Contractions: {profile['contraction_rate']}/1k")

        # Check against defined profile if available.
        if npc_profiles and npc_id in npc_profiles:
            violations = check_voice_consistency(
                " ".join(npc_dialogues[npc_id]),
                npc_profiles[npc_id].get("voice_profile", {}),
            )
            if violations:
                for v in violations:
                    lines.append(f"  [{v['severity'].upper()}] {v['detail']}")
        lines.append("")

    # Cross-NPC bleed.
    bleed = detect_voice_bleed(npc_dialogues)
    if bleed:
        lines.append("### Voice Bleed Findings")
        lines.append("")
        for finding in bleed:
            npc_a, npc_b = finding["npcs"]
            sev = finding["severity"].upper()
            lines.append(f"**[{sev}] {npc_a} / {npc_b}**")
            for signal in finding["signals"]:
                lines.append(f"  - {signal}")
            lines.append("")
    else:
        lines.append("### No voice bleed detected.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python npc_voice.py <archetype>")
        print(f"Available archetypes: {', '.join(VOICE_ARCHETYPES.keys())}")
        sys.exit(1)

    archetype = sys.argv[1]
    if archetype == "list":
        for name, profile in VOICE_ARCHETYPES.items():
            print(f"\n--- {name.upper()} ---")
            for k, v in profile.items():
                if isinstance(v, list):
                    print(f"  {k}:")
                    for item in v:
                        print(f"    - {item}")
                else:
                    print(f"  {k}: {v}")
    elif archetype in VOICE_ARCHETYPES:
        npc = {"name": archetype.capitalize(), "voice_profile": VOICE_ARCHETYPES[archetype]}
        print(build_voice_instructions(npc))
    else:
        print(f"Unknown archetype: {archetype}")
        print(f"Available: {', '.join(VOICE_ARCHETYPES.keys())}")
