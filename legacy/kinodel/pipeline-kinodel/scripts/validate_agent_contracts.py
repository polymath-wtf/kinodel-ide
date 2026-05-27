#!/usr/bin/env python3
"""Validate Kinodel pipeline specs against active capability contracts.

Phase C checks only active/bindable cinematic contracts. Planned capabilities may
exist in the registry but must never satisfy a production binding.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS = ROOT / "contracts" / "capabilities.v1.json"
DEFAULT_SPECS = [ROOT / "pipelines" / "cinematic.v1.json"]
SCHEMA = "kinodel.capability_contracts.v1"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERROR: cannot parse {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} is not a JSON object")
    return data


def index_contracts(contracts: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    if contracts.get("schema") != SCHEMA:
        raise SystemExit(f"ERROR: contracts schema mismatch: {contracts.get('schema')!r} != {SCHEMA!r}")
    active_pipelines = set(str(x) for x in contracts.get("active_pipelines", []))
    caps: dict[str, dict[str, Any]] = {}
    for item in contracts.get("capabilities", []):
        if not isinstance(item, dict) or not item.get("id"):
            raise SystemExit("ERROR: capability entry missing id")
        cid = str(item["id"])
        if cid in caps:
            raise SystemExit(f"ERROR: duplicate capability id {cid}")
        caps[cid] = item
    return caps, active_pipelines


def is_bindable(cap: dict[str, Any]) -> bool:
    return cap.get("status") == "active" and cap.get("bindable") is True


def validate_spec(spec: dict[str, Any], caps: dict[str, dict[str, Any]], active_pipelines: set[str]) -> list[str]:
    errors: list[str] = []
    pipeline_id = str(spec.get("pipeline_id") or "")
    if pipeline_id not in active_pipelines:
        errors.append(f"pipeline {pipeline_id!r} is not active in capability contracts")
    for stage in spec.get("stages", []):
        if not isinstance(stage, dict):
            errors.append("stage is not object")
            continue
        goal = stage.get("goal")
        stage_type = stage.get("type")
        owner = stage.get("owner_skill")
        for cid in stage.get("requires_capabilities", []) or []:
            cap = caps.get(str(cid))
            if not cap:
                errors.append(f"{goal}: unknown required capability {cid}")
                continue
            if not is_bindable(cap):
                errors.append(f"{goal}: required capability {cid} is not active/bindable")
            allowed_types = cap.get("stage_types") or []
            if allowed_types and stage_type not in allowed_types:
                errors.append(f"{goal}: capability {cid} does not allow stage type {stage_type}")
            cap_owner = cap.get("owner_skill")
            if owner and cap_owner and owner != cap_owner:
                errors.append(f"{goal}: owner {owner} does not match capability {cid} owner {cap_owner}")
        if stage_type in {"agent_stage", "montage_stage"} and not stage.get("requires_capabilities"):
            errors.append(f"{goal}: {stage_type} must declare requires_capabilities")
        if stage_type == "render_stage":
            adapter = stage.get("adapter_profile")
            if not adapter:
                errors.append(f"{goal}: render_stage missing adapter_profile")
                continue
            matching = [cap for cap in caps.values() if adapter in (cap.get("adapter_profiles") or [])]
            if not matching:
                errors.append(f"{goal}: adapter_profile {adapter} has no capability contract")
            elif not any(is_bindable(cap) for cap in matching):
                errors.append(f"{goal}: adapter_profile {adapter} is not active/bindable")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", nargs="*", help="pipeline spec JSON files; defaults to cinematic.v1")
    parser.add_argument("--contracts", default=str(DEFAULT_CONTRACTS))
    args = parser.parse_args(argv)
    contracts = load_json(Path(args.contracts).expanduser())
    caps, active_pipelines = index_contracts(contracts)
    paths = [Path(p).expanduser() for p in args.spec] if args.spec else DEFAULT_SPECS
    failed = False
    for path in paths:
        spec = load_json(path)
        errors = validate_spec(spec, caps, active_pipelines)
        if errors:
            failed = True
            print(f"ERROR: {path} failed capability validation:")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"OK: {path} validates against active capability contracts")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
