"""Bounded character uploads and exact, authorized media reads behind the local boundary."""

import asyncio
import base64
import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import Field, model_validator

from backend.characters import (CharacterBio, CharacterRef, CharacterRepository, CharacterSaveReceipt,
                                CharacterV1, ImageDigest, ImageInput, MAX_IMAGE_BYTES, MutationId,
                                Revision, SubjectId)
from backend.domain import DomainModel, _check_depth, _unique_object


MAX_CHARACTER_BODY_BYTES = 84 * 1024 * 1024
MAX_BASE64_CHARS = ((MAX_IMAGE_BYTES + 2) // 3) * 4


class ImageUpload(DomainModel):
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    data_base64: Annotated[str, Field(min_length=4, max_length=MAX_BASE64_CHARS)]


class SavedImage(DomainModel):
    ref: CharacterRef
    image_digest: ImageDigest


class CharacterMutation(DomainModel):
    mutation_id: MutationId
    subject_id: SubjectId | None
    expected_revision: Revision | None
    bio: CharacterBio
    images: Annotated[list[ImageUpload | SavedImage], Field(min_length=1, max_length=6)]

    @model_validator(mode="after")
    def update_pair(self):
        if (self.subject_id is None) != (self.expected_revision is None):
            raise ValueError("Create requires neither identity nor revision; update requires both")
        return self


class CharacterItem(DomainModel):
    ref: CharacterRef
    character: CharacterV1


class CharacterItems(DomainModel):
    items: list[CharacterItem]


def _error(error: Exception) -> HTTPException:
    # The repository's two explicit conflicts are ValueErrors, not HTTP concerns.
    if isinstance(error, FileNotFoundError):
        return HTTPException(404, "Character revision or image not found")
    if isinstance(error, OSError):
        # The manifest may already be committed; the client must replay exact bytes.
        return HTTPException(503, "Character library unavailable")
    if error.args in (("Stale expected_revision",), ("Conflicting mutation payload",)):
        return HTTPException(409, "Character mutation conflict")
    return HTTPException(422, "Invalid character data or library contents")


def _save(root: Path, buffered: bytearray) -> CharacterSaveReceipt:
    body = bytes(buffered)
    _check_depth(body)
    command = CharacterMutation.model_validate(json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object))
    repo = CharacterRepository(root)
    images = []
    for item in command.images:
        if isinstance(item, SavedImage):
            metadata, data = repo.read_image(item.ref, item.image_digest)
            images.append(ImageInput(data, metadata.mime_type))
        else:
            data = base64.b64decode(item.data_base64, validate=True)
            if not 1 <= len(data) <= MAX_IMAGE_BYTES or base64.b64encode(data).decode("ascii") != item.data_base64:
                raise ValueError("Invalid image base64 or size")
            images.append(ImageInput(data, item.mime_type))
    return repo.save(command.bio, images, mutation_id=command.mutation_id,
                     subject_id=command.subject_id, expected_revision=command.expected_revision)


def character_router(root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/characters")

    @router.get("", response_model=CharacterItems)
    async def list_characters():
        def read():
            return {"items": [{"ref": ref, "character": character} for ref, character in CharacterRepository(root).list()]}
        try:
            return await asyncio.to_thread(read)
        except (ValueError, OSError) as error:
            raise _error(error) from error

    @router.get("/{subject_id}", response_model=CharacterItem)
    async def exact_character(subject_id: SubjectId, revision: int = Query(ge=1), digest: ImageDigest = Query()):
        ref = CharacterRef(subject_id=subject_id, revision=revision, digest=digest)
        try:
            character = await asyncio.to_thread(lambda: CharacterRepository(root).read_exact(ref))
            return {"ref": ref, "character": character}
        except (ValueError, OSError) as error:
            raise _error(error) from error

    @router.get("/{subject_id}/images/{image_digest}")
    async def character_image(subject_id: SubjectId, image_digest: ImageDigest,
                              revision: int = Query(ge=1), digest: ImageDigest = Query()):
        ref = CharacterRef(subject_id=subject_id, revision=revision, digest=digest)
        try:
            metadata, data = await asyncio.to_thread(lambda: CharacterRepository(root).read_image(ref, image_digest))
        except (ValueError, OSError) as error:
            raise _error(error) from error
        return Response(data, media_type=metadata.mime_type, headers={"X-Content-Type-Options": "nosniff"})

    @router.post("", response_model=CharacterSaveReceipt)
    async def save_character(request: Request):
        try:
            if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise ValueError("JSON required")
            length = request.headers.get("content-length")
            if length is not None and not 0 <= int(length) <= MAX_CHARACTER_BODY_BYTES:
                raise ValueError("Body too large")
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_CHARACTER_BODY_BYTES:
                    raise ValueError("Body too large")
                body.extend(chunk)
            # JSON/base64 decoding and Pillow/disk work must not hold up the graph runner.
            return await asyncio.to_thread(_save, root, body)
        except (ValueError, OSError) as error:
            raise _error(error) from error

    return router
