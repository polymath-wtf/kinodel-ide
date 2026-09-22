"""Resolve local storage configuration without creating or opening any files."""

import os
from pathlib import Path
import sys


def resolve_data_root() -> Path:
    """Select an absolute data root outside the installation and interpreter."""
    override = os.environ.get("KINODEL_DATA_ROOT")
    if override is not None:
        raw = override
    elif sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise ValueError("LOCALAPPDATA is required; or set KINODEL_DATA_ROOT")
        raw = str(Path(local) / "Kinodel")
    elif sys.platform == "linux":
        raw = str(Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "kinodel")
    else:
        raise ValueError("Set KINODEL_DATA_ROOT on this unsupported platform")

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
    for forbidden in (Path(__file__).resolve().parents[1], Path(sys.prefix).resolve()):
        if root.is_relative_to(forbidden):
            raise ValueError("Data root must be outside the installation and venv")
    if root.exists() and not root.is_dir():
        raise ValueError("Data root must be a directory")
    return root
