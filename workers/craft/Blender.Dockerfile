FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends blender \
    && rm -rf /var/lib/apt/lists/*
ENV HOME=/tmp BLENDER_USER_CONFIG=/tmp/blender-config
ENTRYPOINT ["/usr/bin/blender"]
