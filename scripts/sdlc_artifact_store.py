#!/usr/bin/env python3
"""Repository-independent entrypoint for the shared ArtifactStore CLI."""

import sys
from pathlib import Path


PACKAGES_ROOT = Path(__file__).resolve().parents[1] / "packages"
if str(PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGES_ROOT))

from sdlc_artifact_store.__main__ import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
