#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-mega-game-outer-space}"
MODE="${1:-run}"

docker build -t "$IMAGE_NAME" .

if [ "$MODE" = "smoke" ]; then
  FRAMES="${2:-120}"
  docker run --rm "$IMAGE_NAME" \
    python3 mega_game.py --smoke-test "$FRAMES" --no-music
  exit 0
fi

if [ -z "${DISPLAY:-}" ]; then
  echo "DISPLAY is not set. Start an X server or run './run_docker.sh smoke'."
  exit 1
fi

DATA_DIR="${MEGA_GAME_HOST_DATA_DIR:-$PWD/.container-data}"
mkdir -p "$DATA_DIR"

AUDIO_ARGS=()
HOST_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -S "$HOST_RUNTIME_DIR/pulse/native" ]; then
  AUDIO_ARGS=(
    -e SDL_AUDIODRIVER=pulse
    -e PULSE_SERVER=unix:/tmp/pulse/native
    -v "$HOST_RUNTIME_DIR/pulse:/tmp/pulse:rw"
  )
elif [ -d /dev/snd ]; then
  AUDIO_ARGS=(-e SDL_AUDIODRIVER=alsa --device /dev/snd)
  AUDIO_GROUP_ID="$(getent group audio | cut -d: -f3 || true)"
  if [ -n "$AUDIO_GROUP_ID" ]; then
    AUDIO_ARGS+=(--group-add "$AUDIO_GROUP_ID")
  fi
else
  echo "No host audio socket/device found; the game will run without sound."
fi

XAUTHORITY_FILE="${XAUTHORITY:-$HOME/.Xauthority}"
XAUTH_MOUNT=()
if [ -f "$XAUTHORITY_FILE" ]; then
  XAUTH_MOUNT=(-v "$XAUTHORITY_FILE":"$XAUTHORITY_FILE":ro -e XAUTHORITY="$XAUTHORITY_FILE")
fi

docker run --rm \
  --name mega-game-outer-space \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e DISPLAY="$DISPLAY" \
  -e MEGA_GAME_DATA_DIR=/data \
  -e XDG_RUNTIME_DIR=/tmp \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$DATA_DIR:/data" \
  "${AUDIO_ARGS[@]}" \
  "${XAUTH_MOUNT[@]}" \
  "$IMAGE_NAME"
