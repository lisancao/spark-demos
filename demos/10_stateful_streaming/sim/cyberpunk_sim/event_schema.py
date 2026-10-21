"""Event type registry and envelope builder for Night City simulation events."""

import uuid
from datetime import datetime, timezone
from typing import Any


# Time phases cycle: 6 phases per day, each phase = N ticks
TIME_PHASES = ["dawn", "morning", "afternoon", "evening", "night", "late_night"]
TICKS_PER_PHASE = 50
TICKS_PER_DAY = TICKS_PER_PHASE * len(TIME_PHASES)

# Event type registry — prefix.action
EVENT_TYPES = {
    # Agent actions
    "agent.move", "agent.talk", "agent.attack", "agent.trade",
    "agent.take", "agent.use", "agent.rest", "agent.goal_change",
    "agent.look", "agent.give",
    # Faction dynamics
    "faction.territory_gained", "faction.territory_lost",
    "faction.relation_change", "faction.raid",
    # Economy
    "economy.transaction", "economy.price_change", "economy.supply_shipment",
    # Crime
    "crime.committed", "crime.reported", "crime.ncpd_response",
    # Combat
    "combat.started", "combat.round", "combat.ended",
    # Relationships (NPC-to-NPC network)
    "relationship.change",
    # World events
    "world.weather", "world.disturbance", "world.cyberpsychosis",
    # Missions
    "mission.generated", "mission.stage_advanced", "mission.completed",
}


def sim_time(tick: int) -> dict[str, Any]:
    """Derive sim day, phase, and phase-tick from absolute tick number."""
    day = tick // TICKS_PER_DAY + 1
    phase_index = (tick % TICKS_PER_DAY) // TICKS_PER_PHASE
    phase = TIME_PHASES[phase_index]
    phase_tick = tick % TICKS_PER_PHASE
    return {"sim_day": day, "sim_time_phase": phase, "sim_phase_tick": phase_tick}


def build_event(event_type: str, tick: int, **fields) -> dict[str, Any]:
    """Build a structured event envelope with common metadata + type-specific fields."""
    time_info = sim_time(tick)
    envelope = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sim_tick": tick,
        **time_info,
        **fields,
    }
    return envelope


def build_agent_event(event_type: str, tick: int, npc_id: str, npc_name: str,
                      location_id: str, **fields) -> dict[str, Any]:
    """Build an agent.* event with standard NPC fields."""
    return build_event(
        event_type, tick,
        agent_id=npc_id,
        agent_name=npc_name,
        location_id=location_id,
        **fields,
    )


def build_faction_event(event_type: str, tick: int, faction_id: str,
                        **fields) -> dict[str, Any]:
    """Build a faction.* event."""
    return build_event(event_type, tick, faction_id=faction_id, **fields)


def build_economy_event(event_type: str, tick: int, location_id: str,
                        **fields) -> dict[str, Any]:
    """Build an economy.* event."""
    return build_event(event_type, tick, location_id=location_id, **fields)


def build_crime_event(event_type: str, tick: int, location_id: str,
                      district: str, **fields) -> dict[str, Any]:
    """Build a crime.* event."""
    return build_event(event_type, tick, location_id=location_id, district=district, **fields)


def build_combat_event(event_type: str, tick: int, location_id: str,
                       **fields) -> dict[str, Any]:
    """Build a combat.* event."""
    return build_event(event_type, tick, location_id=location_id, **fields)


def build_relationship_event(tick: int, source_id: str, target_id: str,
                             **fields) -> dict[str, Any]:
    """Build a relationship.change event."""
    return build_event(
        "relationship.change", tick,
        source_id=source_id, target_id=target_id,
        **fields,
    )


def build_world_event(event_type: str, tick: int, **fields) -> dict[str, Any]:
    """Build a world.* event."""
    return build_event(event_type, tick, **fields)


def build_mission_event(event_type: str, tick: int, mission_id: str,
                        **fields) -> dict[str, Any]:
    """Build a mission.* event."""
    return build_event(event_type, tick, mission_id=mission_id, **fields)
