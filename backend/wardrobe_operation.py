"""One bounded Wardrobe service; no graph/start/API/runner activation."""

from pathlib import Path
import sqlite3

from backend.characters import CharacterRepository
from backend.domain import ArtifactRef, OwnerResponseV1
from backend import openrouter_wardrobe as adapter, wardrobe_store as store


async def produce_wardrobe_operation(db: sqlite3.Connection, execution_id: str, approval_request_id: str,
                                    *, character_root: Path) -> tuple[ArtifactRef | OwnerResponseV1, str]:
    """Caller owns open_database for the whole call; no DB transaction spans HTTP."""
    record = store.find_wardrobe_operation(db, execution_id, approval_request_id)
    if record is not None and record["next_activation"] is not None:
        return store.replay_wardrobe_operation(db, record)
    if record is None:
        _, supplied, selected = store.wardrobe_authority(db, execution_id, approval_request_id)
        originals = {}
        repository = CharacterRepository(character_root)
        index = 0
        for card in selected:
            for expected in card.character.images:
                metadata, body = repository.read_image(card.ref, expected.digest)
                if metadata != expected:
                    raise ValueError("Wardrobe image does not match frozen Character snapshot")
                originals[supplied.image_evidence[index].alias] = body
                index += 1
        frozen = await adapter.prepare_wardrobe_request(supplied, originals)
        record = store.prepare_wardrobe_operation(db, execution_id, approval_request_id, frozen, adapter.REPAIR_INSTRUCTION)
    if record["candidate"] is not None:
        return store.commit_wardrobe_operation(db, record["operation_id"])
    while True:
        reserved = store.reserve_wardrobe_attempt(db, record["operation_id"])
        try:
            result = await adapter.complete_wardrobe(reserved["owner_config"],
                repair_instruction=reserved["pins"].repair_instruction if reserved["owner_repairs"] else None)
        except adapter.WardrobeInvalidOutput as error:
            if store.record_wardrobe_invalid(db, record["operation_id"], reserved["owner_attempts"], error):
                continue
            raise adapter.WardrobeInvalidOutput(error.code, "Wardrobe invalid_output; structured repair budget exhausted") from None
        store.pin_wardrobe_candidate(db, record["operation_id"], result)
        return store.commit_wardrobe_operation(db, record["operation_id"])
