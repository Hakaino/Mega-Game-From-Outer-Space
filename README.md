# Mega Game From Outer Space

This was my first big Python project. It is a two-player Pygame platformer with bundled sprite and sound assets.

## Run Locally

Install Pygame, then start the game:

```bash
python3 -m pip install -r requirements.txt
python3 mega_game.py
```

Progress is stored in `progress.json` by default. To edit it:

```bash
python3 edit_progress.py --level 1 --width 1024 --height 768
```

Level layouts live in `levels/levels.json`.

## Check The Code

```bash
python3 -m unittest discover -s tests
python3 level_tools.py
```

## Run In Docker

For a quick headless startup check:

```bash
./run_docker.sh smoke
```

For the interactive game on Linux/X11:

```bash
xhost +local:docker
./run_docker.sh
```

The runner automatically mounts PulseAudio/PipeWire audio when `$XDG_RUNTIME_DIR/pulse/native` exists, and falls back to `/dev/snd` for ALSA hosts. Music is enabled by default unless `progress.json` has `"music": false`.

Container progress is stored on the host in `.container-data/`. Set `MEGA_GAME_HOST_DATA_DIR=/some/path` to use a different folder.
