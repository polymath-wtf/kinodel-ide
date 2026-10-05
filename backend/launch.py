"""Explicit development launcher; the API itself never auto-loads .env."""

import argparse
import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    """Load allowlisted assignments, without interpolation, logging or overriding env."""
    if path.stat().st_size > 65536:
        raise ValueError("Environment file exceeds 64 KiB")
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        key, separator, value = line.strip().removeprefix("export ").partition("=")
        key = key.strip()
        if key not in ("OPENROUTER_API_KEY", "LLM_MODEL", "COMFYUI_LOCAL_ENDPOINT",
                       "COMFYUI_SERVER_ENDPOINT", "COMFYUI_CONNECTION", "COMFYUI_AUTH_TOKEN", "COMFYUI_CA_FILE"):
            continue
        value = value.strip()
        if not separator or key in values:
            raise ValueError(f"Invalid environment assignment at line {number}")
        if value and value[0] in ("'", '"'):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Invalid environment quoting at line {number}")
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if not value and key in ("OPENROUTER_API_KEY", "LLM_MODEL"):
            raise ValueError(f"Invalid environment assignment at line {number}")
        values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the loopback Story workspace with optional explicit environment")
    parser.add_argument("--env-file", type=Path, help="Explicit file; only model/key and ComfyUI connection settings are loaded")
    args = parser.parse_args()
    if args.env_file is not None:
        try:
            load_env_file(args.env_file)
        except (OSError, UnicodeError, ValueError):
            parser.exit(2, "Cannot load the explicit environment file; check its path and assignment syntax.\n")
    import uvicorn
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8765, workers=1, proxy_headers=False)


if __name__ == "__main__":
    main()
