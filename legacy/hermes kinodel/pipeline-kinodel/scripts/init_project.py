#!/usr/bin/env python3
"""Compatibility forwarder for the canonical kinodel-project-layout initializer.

The owned implementation lives at:
  ~/.hermes/skills/kinodel/kinodel-project-layout/scripts/init_project.py
"""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path.home() / ".hermes" / "skills" / "kinodel" / "kinodel-project-layout" / "scripts" / "init_project.py"
runpy.run_path(str(TARGET), run_name="__main__")
