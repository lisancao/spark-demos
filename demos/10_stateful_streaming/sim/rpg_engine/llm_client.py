#!/usr/bin/env python3
"""
LLM Client — Anthropic SDK wrapper with fallback.

Wraps the Claude API for narrative generation. Handles missing SDK,
missing API key, and all API errors gracefully — always returns
fallback text on failure so the game never crashes.
"""

import os
import warnings


def create_client(api_key: str | None = None) -> dict:
    """Initialize LLM config. Reads ANTHROPIC_API_KEY from env if not provided.

    Returns a config dict. The 'available' flag indicates whether the SDK
    and API key are present.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    client = None
    available = False

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            available = True
        except ImportError:
            warnings.warn("anthropic SDK not installed. Running in prompt-only mode.")
        except Exception as exc:
            warnings.warn(f"Failed to initialize Anthropic client: {exc}")

    return {
        "client": client,
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "available": available,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_calls": 0,
    }


def generate_narrative(llm_config: dict, prompt: str,
                       system_message: str = "",
                       fallback_text: str = "") -> dict:
    """Send prompt to Claude, return response.

    Returns:
        {
            "text": str,
            "input_tokens": int,
            "output_tokens": int,
            "source": "llm" | "fallback",
            "error": str,
        }
    """
    if not llm_config.get("available") or not llm_config.get("client"):
        return {
            "text": fallback_text or prompt[:200],
            "input_tokens": 0,
            "output_tokens": 0,
            "source": "fallback",
            "error": "LLM not available",
        }

    client = llm_config["client"]
    model = llm_config.get("model", "claude-sonnet-4-20250514")
    max_tokens = llm_config.get("max_tokens", 1024)

    try:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_message:
            kwargs["system"] = system_message

        response = client.messages.create(**kwargs)

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        input_tokens = getattr(response.usage, "input_tokens", 0)
        output_tokens = getattr(response.usage, "output_tokens", 0)

        llm_config["total_input_tokens"] += input_tokens
        llm_config["total_output_tokens"] += output_tokens
        llm_config["total_calls"] += 1

        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "source": "llm",
            "error": "",
        }

    except Exception as exc:
        error_msg = str(exc)
        warnings.warn(f"LLM call failed: {error_msg}")
        return {
            "text": fallback_text or prompt[:200],
            "input_tokens": 0,
            "output_tokens": 0,
            "source": "fallback",
            "error": error_msg,
        }


def build_system_message(data: dict) -> str:
    """Build the game master system prompt from world_rules.

    Positions the LLM as the game master with agency — it decides what happens
    in the scene based on the player's freeform intent and the world context.
    """
    rules = data.get("world_rules", {})
    if not rules:
        return (
            "You are the Game Master for a text-based RPG.\n"
            "The player's input is freeform intent, not a command to parse. "
            "Decide what happens in the scene, generate consequences and outcomes, "
            "then narrate the result.\n"
            "Write in second person present tense. Keep responses under 300 words."
        )

    parts = [
        "You are the Game Master for a text-based RPG.",
        "",
        "Your role:",
        "- Treat the player's input as freeform intent, not a command to parse.",
        "- Decide what actually happens in the scene based on the situation, the world, and the characters present.",
        "- Generate both consequence and outcome, then narrate the result as vivid prose.",
        "- The world has weight: NPCs have their own agendas, locations have atmosphere, actions have stakes.",
        "",
    ]

    if rules.get("setting"):
        parts.append(f"Setting: {rules['setting']}")
    if rules.get("tone"):
        parts.append(f"Tone: {rules['tone']}")
    if rules.get("era"):
        parts.append(f"Era: {rules['era']}")
    if rules.get("magic_system"):
        parts.append(f"Magic: {rules['magic_system']}")

    combat = rules.get("combat_rules", {})
    if combat:
        parts.append(f"\nCombat: {combat.get('style', '')} Lethality: {combat.get('lethality', '')}")
        if combat.get("note"):
            parts.append(f"Note: {combat['note']}")

    dialogue = rules.get("dialogue_rules", {})
    if dialogue:
        parts.append(f"\nDialogue: {dialogue.get('style', '')}")
        if dialogue.get("trust"):
            parts.append(f"Trust: {dialogue['trust']}")

    parts.extend([
        "",
        "Write in second person present tense ('You step into the tavern.').",
        "Keep responses under 300 words. Show, don't tell.",
        "Use sensory details. End each response leaving the scene open for the player's next move.",
    ])

    return "\n".join(parts)


def get_usage_summary(llm_config: dict) -> str:
    """Formatted token/call stats."""
    if not llm_config.get("total_calls"):
        return "No LLM calls made."

    return (
        f"LLM calls: {llm_config['total_calls']}  "
        f"Input tokens: {llm_config['total_input_tokens']}  "
        f"Output tokens: {llm_config['total_output_tokens']}"
    )
