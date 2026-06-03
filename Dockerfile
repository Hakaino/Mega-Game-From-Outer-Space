FROM debian:bookworm-slim

WORKDIR /app

ENV MEGA_GAME_DATA_DIR=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3 \
    python3-pygame \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 game \
    && mkdir -p /data \
    && chown game:game /data

COPY --chown=game:game . .

USER game
VOLUME ["/data"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "mega_game.py"]
