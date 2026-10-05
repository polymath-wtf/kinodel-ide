"""Pure input/profile diagnostics. Nothing here accepts or authorizes execution.

Registry declarations are preparation evidence, not live rendering capability.
No HTTP, files, storage, approval resolution, RNG or provider effects belong here.
"""

from pydantic import TypeAdapter

from backend import comfyui_workflows as registry
from backend.domain import (
    CinematicDraftV2, FilmmakerInputV2, ImageOnlyInputV1,
    FilmmakerImg2VidUnitV2, FilmmakerRef2VidUnitV2, MotionPlanV2, MotionImg2VidUnitV2,
    ProductionSettingsV2, ProfilePin, SubmittedProductionSettingsV2,
)


def _image_profile() -> dict | None:
    roles, workflows, common_sizes = [], {}, None
    for kind in ("portrait", "background", "sheet", "frame"):
        matches = [spec for spec in registry.WORKFLOWS
                   if spec.preparation_enabled and kind in dict(spec.kinds)]
        if len(matches) != 1:
            return None
        spec = matches[0]
        workflows[spec.id] = registry.workflow_snapshot(spec.id)
        sizes = set(spec.supported_sizes)
        common_sizes = sizes if common_sizes is None else common_sizes & sizes
        roles.append({
            "role": kind, "workflow_id": spec.id, "workflow_version": spec.version,
            "reference_roles": list(dict(spec.kinds)[kind]),
            "supported_sizes": [{"width": w, "height": h} for w, h in spec.supported_sizes],
            "preprocessing": {"crop_policy": dict(spec.mapping.crop_policy),
                              "geometry_rule": spec.mapping.geometry_rule},
            "output": {"media_type": spec.output_media_type, "history_key": spec.output_history_key},
        })
    if not common_sizes:
        return None
    public = {
        "provider": "comfyui", "readiness": "preparation_only", "can_run": False,
        "roles": roles,
        "supported_sizes": [{"width": w, "height": h} for w, h in sorted(common_sizes)],
    }
    identity = {"schema_version": "1", "profile_id": "comfyui-image-preparation", "version": "1",
                **public, "workflows": [workflows[key] for key in sorted(workflows)]}
    pin = ProfilePin(profile_id=identity["profile_id"], version=identity["version"],
                     digest="sha256:" + registry.canonical_digest(identity))
    return {"pin": pin.model_dump(mode="json"), **public}


def production_catalog() -> dict:
    """JSON-safe choices; technical image bundle is visible only as preparation-only.

    Full snapshots participate in its digest but stay private to the adapter.
    Inventory/graph-ready reports cannot promote these declarations to Run.
    """
    image = _image_profile()
    return {
        "schema_version": "1",
        "cinematic": {"image_profiles": [], "video_profiles": [],
                      "default_image_profile": None, "default_video_profile": None,
                      "video_readiness": "unavailable", "can_run": False},
        "image_only": {"profiles": [] if image is None else [image],
                       "default_profile": None, "can_run": False},
    }


def prepare_production(settings: SubmittedProductionSettingsV2 | dict) -> ProductionSettingsV2:
    """Derive exact uniform duration after strict validation; never round/default."""
    submitted: SubmittedProductionSettingsV2 = SubmittedProductionSettingsV2.model_validate(settings, strict=True)
    return ProductionSettingsV2.model_validate({
        **submitted.model_dump(mode="python"),
        "shot_duration_ms": submitted.target_duration_ms // submitted.shot_count,
    }, strict=True)


def _image_pin_issue(pin: ProfilePin | None, profile: dict | None) -> str | None:
    if pin is None:
        return "image_profile_missing"
    if profile is None:
        return "image_profile_unavailable"
    expected = profile["pin"]
    if pin.profile_id != expected["profile_id"]:
        return "image_profile_unknown"
    if pin.model_dump(mode="json") != expected:
        return "image_profile_stale"
    return None


def validate_draft(draft: CinematicDraftV2 | dict) -> dict:
    """Diagnose a draft, never construct a Brief or reserve a start.

    settings_valid covers strict arithmetic/aspect and the exact known image
    bundle's size limits. Video capability/settings remain explicitly unverified.
    Malformed contracts raise ValidationError; unavailable/stale choices are codes.
    """
    value: CinematicDraftV2 = CinematicDraftV2.model_validate(draft, strict=True)
    effective = prepare_production(value.production)
    image = _image_profile()
    issues = []
    image_issue = _image_pin_issue(value.image_profile, image)
    if image_issue is not None:
        issues.append({"code": image_issue, "field": "image_profile"})
    elif image is not None and value.production.image_size.model_dump(mode="json") not in image["supported_sizes"]:
        image_issue = "image_size_unsupported"
        issues.append({"code": image_issue, "field": "production.image_size"})
    else:
        issues.append({"code": "image_preparation_only", "field": "image_profile"})
    issues.extend([
        {"code": "video_profile_missing" if value.video_profile is None else "video_profile_unknown",
         "field": "video_profile"},
        {"code": "video_unverified", "field": "video_profile"},
    ])
    return {
        "schema_version": "1", "settings_valid": image_issue is None,
        "production": effective.model_dump(mode="json"),
        "shot_keys": [f"shot-{number:03d}" for number in range(1, effective.shot_count + 1)],
        "readiness_issues": issues, "can_run": False,
    }


def validate_image_only(value: ImageOnlyInputV1 | dict) -> dict:
    """Return validated preparation input, not permission to run or a stored pin."""
    prepared: ImageOnlyInputV1 = ImageOnlyInputV1.model_validate(value, strict=True)
    image = _image_profile()
    issue = _image_pin_issue(prepared.image_profile, image)
    if issue is not None:
        raise ValueError(issue)
    if image is None or prepared.image_size.model_dump(mode="json") not in image["supported_sizes"]:
        raise ValueError("image_size_unsupported")
    return {"schema_version": "1", "prepared_input": prepared.model_dump(mode="json"),
            "readiness": "preparation_only", "can_run": False}


def validate_motion_plan(plan: MotionPlanV2 | dict, supplied: FilmmakerInputV2 | dict) -> MotionPlanV2:
    """Validate creative output against caller's exact prepared aliases and timing.

    This verifies equality, not repository approval/rights/subject lineage. The
    caller must eventually resolve those before supplying the immutable input.
    No profile, missing role or reference is invented or substituted here.
    """
    candidate: MotionPlanV2 = TypeAdapter(MotionPlanV2).validate_python(plan, strict=True)
    aliases: FilmmakerInputV2 = TypeAdapter(FilmmakerInputV2).validate_python(supplied, strict=True)
    if candidate.video_mode != aliases.video_mode:
        raise ValueError("Motion mode must match supplied mode")
    if candidate.story_ref != aliases.story_ref:
        raise ValueError("Motion Story ref must match the exact supplied ref")
    if [unit.unit_key for unit in candidate.units] != [unit.unit_key for unit in aliases.units]:
        raise ValueError("Motion shot keys and order must match supplied keys")
    for unit, expected in zip(candidate.units, aliases.units, strict=True):
        if unit.duration_ms != expected.duration_ms:
            raise ValueError("Motion duration must match the exact supplied duration")
        if isinstance(unit, MotionImg2VidUnitV2):
            if not isinstance(expected, FilmmakerImg2VidUnitV2) or unit.start_frame != expected.start_frame:
                raise ValueError("Motion start frame must match the exact supplied selector")
        elif not isinstance(expected, FilmmakerRef2VidUnitV2) or unit.reference_images != expected.reference_images:
            raise ValueError("Motion reference images must match the exact ordered supplied selectors")
    return candidate
