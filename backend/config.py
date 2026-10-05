"""Resolve local storage configuration without creating or opening any files."""

import os
from pathlib import Path
import sys


def resolve_data_root() -> Path:
    """Default to installation/stuff; keep other source paths and the venv protected."""
    installation = Path(__file__).resolve().parents[1]
    override = os.environ.get("KINODEL_DATA_ROOT")
    raw = override if override is not None else str(installation / "stuff")

    # Normalize the extended local-drive spelling before containment checks.
    if os.name == "nt" and raw.startswith("\\\\?\\") and len(raw) >= 7 and raw[5:7] == ":\\":
        raw = raw[4:]
    if raw.startswith(("\\\\", "//")):
        raise ValueError("Network and device data roots are unsupported")
    if not raw or not Path(raw).is_absolute():
        raise ValueError("Data root must be an absolute local path")
    root = Path(raw).resolve()
    if str(root).startswith(("\\\\", "//")):
        raise ValueError("Network data roots are unsupported")
    if root.is_relative_to(installation) and not root.is_relative_to(installation / "stuff"):
        raise ValueError("Data root must be outside installation source paths")
    if root.is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("Data root must be outside the venv")
    if root.exists() and not root.is_dir():
        raise ValueError("Data root must be a directory")
    return root
