ARG CRAFT_RUNTIME_IMAGE=clicko-craft-runtime:local
FROM ${CRAFT_RUNTIME_IMAGE}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates dumb-init ffmpeg python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/clicko
COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv /opt/clicko/venv \
    && /opt/clicko/venv/bin/pip install --no-cache-dir --requirement backend/requirements.txt
COPY backend/app ./backend/app
COPY workers/media-cpu/worker.manifest.json ./worker-manifest.json
RUN install -d -o clicko -g clicko /var/lib/clicko /tmp/clicko-craft

ENV PATH="/opt/clicko/venv/bin:${PATH}" \
    PYTHONPATH="/opt/clicko/backend" \
    OBJECT_STORAGE_BACKEND="s3" \
    STUDIO_ISOLATED_QUEUES_ENABLED="true" \
    STUDIO_WORKER_MANIFEST_PATH="/opt/clicko/worker-manifest.json" \
    STUDIO_WORKER_CAPABILITY="media_cpu" \
    STUDIO_CRAFT_PHOTOCRAFT_BINARY="/opt/clicko/bin/clicko-photocraft-adapter" \
    STUDIO_CRAFT_FILMCRAFT_BINARY="/opt/clicko/bin/clicko-filmcraft-adapter" \
    STUDIO_CRAFT_EFFECTCRAFT_BINARY="/opt/clicko/bin/clicko-effectcraft-adapter" \
    PHOTOCRAFT_NO_SYSTEM_FONTS="1" \
    FFMPEG_PATH="/usr/bin/ffmpeg" \
    FFPROBE_PATH="/usr/bin/ffprobe" \
    TMPDIR="/tmp/clicko-craft"

USER clicko
WORKDIR /opt/clicko/backend
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A app.celery_app:celery_app inspect ping --destination "celery@$HOSTNAME" --timeout 5 | grep -q pong
CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "--loglevel=INFO", "--queues=studio.media.cpu", "--concurrency=1", "--prefetch-multiplier=1"]
