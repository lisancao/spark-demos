#!/usr/bin/env bash
# Setup and smoke-test both demos end-to-end.
# Run from the repo root: bash setup.sh
#
# Requires: uv (https://github.com/astral-sh/uv), Docker
# Optional: set SPARK_IMAGE before running if you've pulled a newer image.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}!${NC}  $*"; }
fail() { echo -e "  ${RED}✗${NC}  $*"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Spark 4.2 demos — local setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Demo 1: metrics_views ──────────────────────────────────────────────────
echo ""
echo "▶  Demo 1: Metric Views"

DEMO1="$REPO_ROOT/demos/01_metrics_views"
cd "$DEMO1"

if [ ! -d ".venv" ]; then
    echo "   Creating venv…"
    uv venv .venv
fi

echo "   Installing dependencies…"
uv pip install -e ".[dev]" --quiet
ok "metrics-views-demo installed"

echo "   Generating dataset…"
.venv/bin/python -m metrics_views_demo.generate_data
ok "data generated"

# ── 2. Demo 2: spark_connect ──────────────────────────────────────────────────
echo ""
echo "▶  Demo 2: Spark Connect"

DEMO2="$REPO_ROOT/demos/02_spark_connect"
cd "$DEMO2"

if [ ! -d ".venv" ]; then
    echo "   Creating venv…"
    uv venv .venv
fi

echo "   Installing dependencies…"
uv pip install -e ".[dev]" --quiet
ok "spark-connect-demo installed"

# ── 3. Smoke-test: beats 1–4 locally (no server required) ────────────────────
echo ""
echo "▶  Smoke test: Demo 1 beats 1–4 (SPARK_LOCAL=1, no server needed)"
cd "$DEMO1"
SPARK_LOCAL=1 .venv/bin/python -m metrics_views_demo.run_footgun --no-color
ok "beats 1–4 passed"

# ── 4. Start the sandbox server ───────────────────────────────────────────────
echo ""
echo "▶  Starting Spark 4.2 sandbox server…"
cd "$REPO_ROOT"

IMAGE="${SPARK_IMAGE:-lakehouse/spark:5.0.0-snapshot-cdc}"
echo "   image: $IMAGE"

if ! docker image inspect "$IMAGE" &>/dev/null; then
    warn "Image $IMAGE not found locally — attempting pull…"
    docker pull "$IMAGE" || {
        fail "Could not pull $IMAGE"
        echo ""
        echo "   Set SPARK_IMAGE to an available image and re-run, e.g.:"
        echo "     SPARK_IMAGE=apache/spark:4.2.0 bash setup.sh"
        echo ""
        echo "   Available tags: https://hub.docker.com/r/apache/spark/tags"
        exit 1
    }
fi

SPARK_IMAGE="$IMAGE" docker compose -p spark42demos -f compose/docker-compose.yml up -d
echo "   Waiting for Connect gRPC to be ready on :15099…"
for i in $(seq 1 20); do
    if nc -z localhost 15099 2>/dev/null; then
        ok "Connect server is up"
        break
    fi
    [ $i -eq 20 ] && { fail "Server didn't come up after 20s"; exit 1; }
    sleep 1
done

# ── 5. Full demo 1 (beats 5–6 require the server) ────────────────────────────
echo ""
echo "▶  Full Demo 1 (beats 5–6: metric-view DDL + MEASURE())"
cd "$DEMO1"
.venv/bin/python -m metrics_views_demo.run_footgun --no-color
ok "Demo 1 complete"

# ── 6. Demo 2: thin client + AI tool ─────────────────────────────────────────
echo ""
echo "▶  Demo 2: thin client"
cd "$DEMO2"
.venv/bin/python -m spark_connect_demo.thin_client

echo ""
echo "▶  Demo 2: AI tool (reads metric view from Demo 1)"
.venv/bin/python -m spark_connect_demo.ai_tool
ok "Demo 2 complete"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  All done. Server is still running."
echo ""
echo "  To launch the notebooks:"
echo "    cd demos/01_metrics_views && .venv/bin/jupyter lab notebooks/"
echo ""
echo "  To stop the server:"
echo "    docker compose -p spark42demos -f compose/docker-compose.yml down"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
