#!/usr/bin/env python3
"""
ASCII Map Renderer — Generate text-based maps from location graphs.

Reads the location graph (connections with cardinal directions) and renders
an ASCII map with:
  - Node boxes for each location
  - Directional edges (|, ---)
  - Player position marker [*]
  - Blocked path markers (X)
  - Location state indicators (!, ~, ?)
  - NPC presence dots
"""

from typing import Any, Optional


# ---------------------------------------------------------------------------
# Direction vectors
# ---------------------------------------------------------------------------

DIR_OFFSETS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}

REVERSE_DIR = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
}

# Cell dimensions (characters).
CELL_W = 20   # Width of a location box.
CELL_H = 3    # Height of a location box.
GAP_H = 3     # Vertical gap between rows (for connection lines).
GAP_W = 5     # Horizontal gap between columns (for connection lines).


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------

def _build_graph(locations: list[dict]) -> dict[str, list[dict]]:
    """Build adjacency list: {loc_id: [{to, direction, blocked_by}, ...]}."""
    graph = {}
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        loc_id = loc.get("id", "")
        if not loc_id:
            continue
        edges = []
        for conn in loc.get("connections", []):
            if isinstance(conn, str):
                edges.append({"to": conn, "direction": "", "blocked_by": None})
            elif isinstance(conn, dict):
                edges.append({
                    "to": conn.get("to", ""),
                    "direction": conn.get("direction", ""),
                    "blocked_by": conn.get("blocked_by"),
                })
        graph[loc_id] = edges
    return graph


def _location_lookup(locations: list[dict]) -> dict[str, dict]:
    """Build {loc_id: location_dict} lookup."""
    return {loc["id"]: loc for loc in locations
            if isinstance(loc, dict) and loc.get("id")}


# ---------------------------------------------------------------------------
# Node placement (BFS from start)
# ---------------------------------------------------------------------------

def _place_nodes(graph: dict, start: str) -> dict[str, tuple[int, int]]:
    """BFS placement on a 2D grid. Returns {loc_id: (col, row)}."""
    placements = {}
    occupied = set()  # (col, row) positions already taken.

    if start not in graph:
        # Fallback: use first node.
        start = next(iter(graph)) if graph else ""
    if not start:
        return placements

    placements[start] = (0, 0)
    occupied.add((0, 0))

    queue = [start]
    visited = {start}

    while queue:
        current = queue.pop(0)
        cx, cy = placements[current]

        for edge in graph.get(current, []):
            target = edge["to"]
            if target in visited or target not in graph:
                continue

            direction = edge.get("direction", "")
            dx, dy = DIR_OFFSETS.get(direction, (0, 0))

            if dx == 0 and dy == 0:
                # No direction specified — try to find an open adjacent spot.
                dx, dy = _find_open_spot(cx, cy, occupied)

            # Try the natural position first.
            nx, ny = cx + dx, cy + dy

            # Handle collisions — nudge until we find an open spot.
            attempts = 0
            while (nx, ny) in occupied and attempts < 20:
                attempts += 1
                # Try further in the same direction.
                nx += dx if dx != 0 else 0
                ny += dy if dy != 0 else 0
                if (nx, ny) in occupied:
                    # Try perpendicular offset.
                    if dx != 0:
                        ny += (1 if attempts % 2 == 0 else -1)
                    else:
                        nx += (1 if attempts % 2 == 0 else -1)

            placements[target] = (nx, ny)
            occupied.add((nx, ny))
            visited.add(target)
            queue.append(target)

    return placements


def _find_open_spot(cx: int, cy: int, occupied: set) -> tuple[int, int]:
    """Find the first open adjacent position."""
    for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
        if (cx + dx, cy + dy) not in occupied:
            return dx, dy
    # All adjacent taken — go further.
    for dist in range(2, 10):
        for dx, dy in [(dist, 0), (0, dist), (-dist, 0), (0, -dist)]:
            if (cx + dx, cy + dy) not in occupied:
                return dx, dy
    return (1, 0)


# ---------------------------------------------------------------------------
# ASCII rendering
# ---------------------------------------------------------------------------

def render_ascii_map(data: dict, player_location: str = "",
                     show_blocked: bool = True,
                     show_npcs: bool = True) -> str:
    """Render the location graph as an ASCII map.

    Args:
        data: game data dict (must contain 'locations' and optionally 'npcs')
        player_location: location_id to mark with [*]
        show_blocked: show blocked path markers
        show_npcs: show NPC count at locations

    Returns:
        Multi-line ASCII string.
    """
    locations = data.get("locations", [])
    if not locations:
        return "  (no locations)"

    loc_lookup = _location_lookup(locations)
    graph = _build_graph(locations)

    if not graph:
        return "  (no connections)"

    # Get player location if not provided.
    if not player_location:
        player = data.get("player", {})
        if isinstance(player, dict):
            player_location = player.get("location", "")

    # Count NPCs per location.
    npc_counts = {}
    if show_npcs:
        for npc in data.get("npcs", []):
            if isinstance(npc, dict):
                loc = npc.get("location", "")
                npc_counts[loc] = npc_counts.get(loc, 0) + 1

    # Place nodes.
    placements = _place_nodes(graph, player_location or next(iter(graph)))

    if not placements:
        return "  (could not place locations)"

    # Normalize to 0-based coordinates.
    min_x = min(p[0] for p in placements.values())
    min_y = min(p[1] for p in placements.values())
    placements = {k: (v[0] - min_x, v[1] - min_y) for k, v in placements.items()}

    max_x = max(p[0] for p in placements.values())
    max_y = max(p[1] for p in placements.values())

    # Create a character grid.
    grid_w = (max_x + 1) * (CELL_W + GAP_W)
    grid_h = (max_y + 1) * (CELL_H + GAP_H)
    grid = [[' '] * grid_w for _ in range(grid_h)]

    # Reverse lookup: (col, row) -> loc_id.
    pos_to_loc = {v: k for k, v in placements.items()}

    # Draw location boxes.
    for loc_id, (col, row) in placements.items():
        loc = loc_lookup.get(loc_id, {})
        _draw_box(grid, col, row, loc, loc_id,
                  is_player=(loc_id == player_location),
                  npc_count=npc_counts.get(loc_id, 0))

    # Draw connections.
    drawn_edges = set()
    for loc_id, edges in graph.items():
        if loc_id not in placements:
            continue
        for edge in edges:
            target = edge["to"]
            if target not in placements:
                continue
            edge_key = tuple(sorted([loc_id, target]))
            if edge_key in drawn_edges:
                continue
            drawn_edges.add(edge_key)

            blocked = edge.get("blocked_by") is not None
            _draw_connection(grid, placements[loc_id], placements[target],
                            blocked=blocked and show_blocked)

    # Convert grid to string.
    lines = [''.join(row).rstrip() for row in grid]

    # Trim empty lines at top and bottom.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    # Add legend.
    legend = [
        "",
        "  Legend: [*] = you  [!] = danger  [~] = special  X = blocked",
    ]

    return '\n'.join(lines) + '\n'.join(legend)


def _draw_box(grid: list[list[str]], col: int, row: int,
              loc: dict, loc_id: str,
              is_player: bool = False,
              npc_count: int = 0):
    """Draw a location box on the grid."""
    # Pixel position.
    px = col * (CELL_W + GAP_W)
    py = row * (CELL_H + GAP_H)

    # State indicator.
    state = loc.get("state", "normal")
    tags = loc.get("tags", [])
    indicator = " "
    if is_player:
        indicator = "*"
    elif state == "dormant":
        indicator = "~"
    elif "dangerous" in tags:
        indicator = "!"
    elif "mystery" in tags or "sacred" in tags:
        indicator = "?"

    # Location name (truncate to fit).
    name = loc.get("name", loc_id)
    max_name = CELL_W - 4
    if len(name) > max_name:
        name = name[:max_name - 1] + "."

    # NPC dots.
    npc_str = ""
    if npc_count > 0:
        npc_str = "." * min(npc_count, 4)

    # Top border.
    top = "+" + "-" * (CELL_W - 2) + "+"
    # Content line.
    content = f"|{indicator} {name}"
    content = content.ljust(CELL_W - 1) + "|"
    # NPC line.
    if npc_str:
        npc_line = f"|  {npc_str}"
        npc_line = npc_line.ljust(CELL_W - 1) + "|"
    else:
        npc_line = "|" + " " * (CELL_W - 2) + "|"
    # Bottom border.
    bottom = "+" + "-" * (CELL_W - 2) + "+"

    lines = [top, content, npc_line, bottom]

    # Write to grid.
    for dy, line in enumerate(lines):
        for dx, ch in enumerate(line):
            gy = py + dy
            gx = px + dx
            if 0 <= gy < len(grid) and 0 <= gx < len(grid[0]):
                grid[gy][gx] = ch


def _draw_connection(grid: list[list[str]],
                     pos_a: tuple[int, int], pos_b: tuple[int, int],
                     blocked: bool = False):
    """Draw a connection line between two node positions."""
    ax, ay = pos_a
    bx, by = pos_b

    # Pixel centers of each box.
    a_px = ax * (CELL_W + GAP_W) + CELL_W // 2
    a_py = ay * (CELL_H + GAP_H) + CELL_H // 2
    b_px = bx * (CELL_W + GAP_W) + CELL_W // 2
    b_py = by * (CELL_H + GAP_H) + CELL_H // 2

    if ay == by:
        # Horizontal connection.
        left_x = min(a_px, b_px) + CELL_W // 2 + 1
        right_x = max(a_px, b_px) - CELL_W // 2
        y = a_py
        mid_x = (left_x + right_x) // 2

        for x in range(left_x, right_x):
            if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                if blocked and x == mid_x:
                    grid[y][x] = 'X'
                else:
                    grid[y][x] = '-'

    elif ax == bx:
        # Vertical connection.
        top_y = min(a_py, b_py) + 2  # Below the box bottom.
        bottom_y = max(a_py, b_py) - 1  # Above the box top.
        x = a_px
        mid_y = (top_y + bottom_y) // 2

        for y in range(top_y, bottom_y):
            if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
                if blocked and y == mid_y:
                    grid[y][x] = 'X'
                else:
                    grid[y][x] = '|'

    else:
        # Diagonal — draw an L-shaped connection (horizontal then vertical).
        # Go horizontal first from A, then vertical to B.
        mid_x = b_px
        y1 = a_py
        y2 = b_py

        # Horizontal segment.
        sx = min(a_px + CELL_W // 2 + 1, mid_x)
        ex = max(a_px + CELL_W // 2 + 1, mid_x)
        for x in range(sx, ex + 1):
            if 0 <= y1 < len(grid) and 0 <= x < len(grid[0]):
                grid[y1][x] = '-'

        # Vertical segment.
        sy = min(y1, y2 - 1)
        ey = max(y1, y2 - 1)
        for y in range(sy, ey + 1):
            if 0 <= y < len(grid) and 0 <= mid_x < len(grid[0]):
                if grid[y][mid_x] == '-':
                    grid[y][mid_x] = '+'
                else:
                    grid[y][mid_x] = '|'

        # Blocked marker at bend.
        if blocked:
            bend_y = y1
            if 0 <= bend_y < len(grid) and 0 <= mid_x < len(grid[0]):
                grid[bend_y][mid_x] = 'X'


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
    from game_state import load_game_data, get_player

    if len(sys.argv) < 2:
        print("Usage: python map_renderer.py <game_data_dir>")
        sys.exit(1)

    game_dir = sys.argv[1]
    data = load_game_data(game_dir)
    player = get_player(data)
    player_loc = player.get("location", "")

    print(render_ascii_map(data, player_location=player_loc))
