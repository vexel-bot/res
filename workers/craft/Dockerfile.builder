FROM rust:1.95-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config build-essential clang libclang-dev libasound2-dev \
    libfontconfig1-dev libxkbcommon-dev libgtk-3-dev libssl-dev \
    libegl1-mesa-dev ffmpeg ca-certificates python3 nodejs npm \
    && rm -rf /var/lib/apt/lists/*
RUN rustup target add wasm32-unknown-unknown
ENV CARGO_HOME=/cargo CARGO_TARGET_DIR=/target CARGO_BUILD_JOBS=2
WORKDIR /workspace
