FROM debian:bookworm-slim

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates dumb-init ffmpeg python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home clicko

WORKDIR /opt/clicko
COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv /opt/clicko/venv \
    && /opt/clicko/venv/bin/pip install --no-cache-dir --requirement backend/requirements.txt
COPY backend/requirements-rea-video.txt ./backend/requirements-rea-video.txt
RUN python3 -m venv /opt/clicko/rea-video \
    && /opt/clicko/rea-video/bin/pip install --no-cache-dir --requirement backend/requirements-rea-video.txt
COPY backend/app ./backend/app
COPY backend/scripts/provision_moneyprinterturbo.py ./backend/scripts/
COPY docs/studios/knowledge/reference-evidence ./docs/studios/knowledge/reference-evidence
COPY workers/media-cpu/worker.manifest.json ./worker-manifest.json
RUN CLICKO_MPT_ROOT=/opt/clicko/moneyprinterturbo /opt/clicko/venv/bin/python backend/scripts/provision_moneyprinterturbo.py \
    && install -d -o clicko -g clicko /var/lib/clicko /tmp/clicko-media

ENV PATH="/opt/clicko/venv/bin:${PATH}" \
    PYTHONPATH="/opt/clicko/backend" \
    OBJECT_STORAGE_BACKEND="s3" \
    STUDIO_ISOLATED_QUEUES_ENABLED="true" \
    STUDIO_WORKER_MANIFEST_PATH="/opt/clicko/worker-manifest.json" \
    STUDIO_WORKER_CAPABILITY="media_cpu" \
    CLICKO_MPT_ROOT="/opt/clicko/moneyprinterturbo" \
    STUDIO_CRAFT_REA_VIDEO_BINARY="/opt/clicko/rea-video/bin/rea-video" \
    FFMPEG_PATH="/usr/bin/ffmpeg" \
    FFPROBE_PATH="/usr/bin/ffprobe" \
    TMPDIR="/tmp/clicko-media"

USER clicko
WORKDIR /opt/clicko/backend
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A app.celery_app:celery_app inspect ping --destination "celery@$HOSTNAME" --timeout 5 | grep -q pong
CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "--loglevel=INFO", "--queues=studio.media.cpu", "--concurrency=1", "--prefetch-multiplier=1"]
