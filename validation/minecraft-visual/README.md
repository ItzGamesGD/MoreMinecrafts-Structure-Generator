# SG-01 Minecraft 26.3 visual acceptance fixture

A temporary Fabric Loom client/server launches Minecraft 26.3 with Java 25. The acceptance workflow copies the generated SG-01 datapack byte-for-byte into a disposable server world before startup, verifies the pack is enabled, attempts the five resource-derived `/place template` IDs and the Jigsaw `/place structure` ID, then connects a real graphical client under Xvfb/llvmpipe. RCON camera teleports and Minecraft's F2 screenshot action produce the PNG evidence.

Run from repository root on Linux with Java 25, Xvfb, Openbox, Mesa llvmpipe, xdotool, ImageMagick and Python 3:

```sh
python3 examples/forgotten_kingdom/build_cavern.py /tmp/sg01-datapack
validation/minecraft-visual/run-runtime-visual.sh "$PWD" /tmp/sg01-datapack
```

The combined runner keeps the server alive through client capture. GitHub Actions tears down background processes at step boundaries, so server acceptance and client screenshots must run in one step. Placement test chunks are force-loaded before commands; each template and the Jigsaw structure must return a successful placement result.

The validation mod fixture contains no gameplay code or content. Logs and PNGs are written under `validation/minecraft-visual/evidence/` and `run/logs/`. The workflow uploads these as a downloadable artifact. `capture-session.sh` documents fixed coordinates and yaw/pitch in `evidence/camera-positions.log`; screenshots are native Minecraft F2 captures at 1280×720.
