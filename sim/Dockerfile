FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY rpg_engine/ /app/rpg_engine/
COPY cyberpunk_sim/ /app/cyberpunk_sim/
COPY replay.py /app/replay.py

VOLUME /output
ENV SIM_SEED=42 \
    SIM_TICK_MS=100 \
    SIM_AGENTS_PER_TICK=10 \
    SIM_MAX_TICKS=0 \
    SIM_OUTPUT_DIR=/output \
    SIM_LOG_LEVEL=INFO \
    SIM_STDOUT_EVENTS=0 \
    PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "cyberpunk_sim.city_sim"]
