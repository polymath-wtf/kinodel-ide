"""Frozen Story→Wardrobe→anchor batch admission; graph delivery is a separate slice."""

from pathlib import Path
import sqlite3
from typing import Literal

from backend import config, production
from backend.batch_generation import BatchConnectionPinV1, resolve_batch_image_profile
from backend.characters import CharacterRef
from backend.domain import (CanonicalUUID, Digest, DomainModel, ExactProfilePin, MediaSize, StoryTextInputV1,
                            sha256_digest)
from backend.openrouter import StoryWardrobeOwnerConfigV2


GRAPH_ID = "kinodel.story-anchor-batch"
GRAPH_VERSION = "1"
GRAPH_DIGEST = sha256_digest(
    b"kinodel.story-anchor-batch.v1:frozen-story-wardrobe-v2+start-render-intent>storytell>story_prepare_review>story_wait>story_apply>wardrobe>prepare_anchor_batch>batch_wait>exact_join>END|clarify+revise>storytell")


class AnchorRenderIntentV1(DomainModel):
    image_size: MediaSize
    image_profile: ExactProfilePin
    connection: BatchConnectionPinV1


class StoryAnchorOwnerConfigV1(StoryWardrobeOwnerConfigV2):
    """Explicit new schema; historical owner configs still reject these fields."""

    schema_id: Literal["story_anchor_start"]
    schema_version: Literal["1"]
    render_intent: AnchorRenderIntentV1


class StoryAnchorGraphV1(DomainModel):
    id: Literal["kinodel.story-anchor-batch"] = GRAPH_ID
    version: Literal["1"] = GRAPH_VERSION
    digest: Digest = GRAPH_DIGEST


class StoryAnchorStartOptionsV1(DomainModel):
    schema_version: Literal["1"] = "1"
    graph: StoryAnchorGraphV1
    image_profile: ExactProfilePin
    supported_sizes: list[MediaSize]
    connections: list[BatchConnectionPinV1]


class StoryAnchorStartReceiptV1(DomainModel):
    execution_id: CanonicalUUID
    work_id: CanonicalUUID
    graph: StoryAnchorGraphV1
    render_intent: AnchorRenderIntentV1


def story_anchor_start_options() -> StoryAnchorStartOptionsV1:
    """Local declarations/configuration only, not provider readiness or authorization."""
    profiles = production.production_catalog()["image_only"]["profiles"]
    if len(profiles) != 1:
        raise ValueError("Anchor image profile is unavailable")
    profile = profiles[0]
    connections = []
    for name in ("local", "server"):
        try:
            selected = config.resolve_comfyui_connection(name)
        except config.ComfyUIConfigError:
            continue
        connections.append(BatchConnectionPinV1(connection=name, endpoint_digest="sha256:" + selected.endpoint_digest))
    return StoryAnchorStartOptionsV1(graph=StoryAnchorGraphV1(), image_profile=profile["pin"],
        supported_sizes=profile["supported_sizes"], connections=connections)


def validate_anchor_render_intent(intent: AnchorRenderIntentV1) -> None:
    """Fresh admission only; replay must not consult current declarations/settings."""
    resolve_batch_image_profile(intent.image_profile, intent.image_size)
    selected = config.resolve_comfyui_connection(intent.connection.connection)
    if intent.connection.endpoint_digest != "sha256:" + selected.endpoint_digest:
        raise ValueError("Anchor configured connection identity changed")


async def start_story_anchor_batch(db: sqlite3.Connection, saver, project_id: str, client_key: str,
                                   shot_ids: list[str], brief: StoryTextInputV1, *,
                                   render_intent: AnchorRenderIntentV1 | dict,
                                   character_refs: list[CharacterRef] | None = None,
                                   character_root: Path | None = None) -> StoryAnchorStartReceiptV1:
    from backend.story_start import DEFAULT_CHARACTER_ROOT, _start_live_story

    intent = AnchorRenderIntentV1.model_validate(render_intent)
    receipt = await _start_live_story(db, saver, project_id, client_key, shot_ids, brief,
        wardrobe=True, render_intent=intent, character_refs=character_refs,
        character_root=DEFAULT_CHARACTER_ROOT if character_root is None else character_root)
    # Acceptance/replay returns the stored intent, never today's settings.
    from backend.openrouter import read_owner_config
    owner = read_owner_config(db.execute("SELECT owner_config FROM executions WHERE execution_id=?",
                                         (receipt.execution_id,)).fetchone()[0])
    if not isinstance(owner, StoryAnchorOwnerConfigV1):
        raise ValueError("Anchor Start configuration mismatch")
    return StoryAnchorStartReceiptV1(execution_id=receipt.execution_id, work_id=receipt.work_id,
                                    graph=StoryAnchorGraphV1(), render_intent=owner.render_intent)
