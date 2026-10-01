FROM node:22.15.0-bookworm-slim@sha256:01cbafb3480d272d73613e5e74206ec79326f4a9ebb4d089f636b53d12d87a04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        dumb-init \
        ffmpeg \
        fonts-liberation \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/clicko

COPY workers/media-cpu/package.json workers/media-cpu/package-lock.json ./media-runtime/
RUN cd media-runtime \
    && npm ci --omit=dev --no-audit --no-fund \
    && npm cache clean --force

COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv /opt/clicko/venv \
    && /opt/clicko/venv/bin/pip install --no-cache-dir --requirement backend/requirements.txt

COPY backend ./backend
COPY workers/media-cpu/worker.manifest.json ./worker-manifest.json

RUN useradd --create-home --uid 10001 clicko \
    && install -d -o clicko -g clicko /var/lib/clicko /tmp/clicko-hyperframes

ENV PATH="/opt/clicko/venv/bin:/opt/clicko/media-runtime/node_modules/.bin:${PATH}" \
    PYTHONPATH="/opt/clicko/backend" \
    HOME="/home/clicko" \
    OBJECT_STORAGE_BACKEND="s3" \
    STUDIO_ISOLATED_QUEUES_ENABLED="true" \
    STUDIO_WORKER_MANIFEST_PATH="/opt/clicko/worker-manifest.json" \
    STUDIO_WORKER_CAPABILITY="media_cpu" \
    HYPERFRAMES_ENABLED="true" \
    HYPERFRAMES_NODE_PATH="/usr/local/bin/node" \
    HYPERFRAMES_CLI_PATH="/opt/clicko/media-runtime/node_modules/hyperframes/bin/hyperframes.mjs" \
    HYPERFRAMES_BROWSER_PATH="/usr/bin/chromium" \
    PRODUCER_BROWSER_GPU_MODE="software" \
    FFMPEG_PATH="/usr/bin/ffmpeg" \
    STUDIO_UGC_FONT_PATH="/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" \
    FFPROBE_PATH="/usr/bin/ffprobe" \
    TMPDIR="/tmp/clicko-hyperframes"

USER clicko
WORKDIR /opt/clicko/backend

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A app.celery_app:celery_app inspect ping --destination "celery@$HOSTNAME" --timeout 5 | grep -q pong
CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "--loglevel=INFO", "--queues=studio.media.cpu", "--concurrency=1", "--prefetch-multiplier=1"]
