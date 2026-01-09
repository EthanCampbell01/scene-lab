"""scene-kit/gen_scene.py

Backwards-compatible wrapper.

Use this when you want the old command to still work:

  python gen_scene.py --brief "..." --variant cia-safe-house --provider ollama

Under the hood it now calls `pipeline.py`, which produces a valid expanded scene
and automatically copies it to `previewer/public/latest.json`.
"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    here = os.path.dirname(__file__)
    pipeline = os.path.join(here, "pipeline.py")

    # Pass through ALL args to pipeline.
    cmd = [sys.executable, pipeline, *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
