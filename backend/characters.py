"""Local creator-authored cards, not generated CharacterChunks or runtime canon.

Calling save is the creator's explicit acceptance. The caller supplies the library
root (normally repo/wiki/characters); reads never bootstrap it. One atomic manifest
commits current refs and replay receipts after immutable JSON/images are published.
Interrupted saves can leave invisible unreferenced files; no automatic cleanup.
The managed root must be trusted against concurrent hostile filesystem replacement,
as with own_data_root. Windows supports process-death recovery, not power-loss fsync
of directory entries. No database, cloud, indexing or model calls are involved.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import stat
import tempfile
from typing import Annotated, Literal
from uuid import uuid4
import warnings

from PIL import Image, ImageOps
from pydantic import AfterValidator, Field, model_validator

from backend.database import _check_file, _sync_directory
from backend.domain import DomainModel, MAX_JSON_BYTES, canonical_json, parse_json_model, sha256_digest
from backend.ownership import own_data_root


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_SIDE = 8192
MAX_IMAGE_PIXELS = 16_000_000
_FORMATS = {"image/png": ("PNG", "png"), "image/jpeg": ("JPEG", "jpg"),
            "image/webp": ("WEBP", "webp")}
SubjectId = Annotated[str, Field(pattern=r"^character-[0-9a-f]{32}$")]
ImageDigest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
Revision = Annotated[int, Field(ge=1)]
MutationId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")]


def _text(value: str) -> str:
    if not value.strip() or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("Text must be nonblank and contain no control characters")
    value.encode("utf-8")
    return value


Name = Annotated[str, Field(min_length=1, max_length=200), AfterValidator(_text)]
ShortText = Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_text)]
Vibe = Annotated[str, Field(min_length=1, max_length=4096), AfterValidator(_text)]


class CharacterBio(DomainModel):
    name: Name
    age: ShortText | None = None
    gender: ShortText | None = None
    vibe: Vibe | None = None


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str


class CharacterImage(DomainModel):
    digest: ImageDigest
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    byte_length: Annotated[int, Field(ge=1, le=MAX_IMAGE_BYTES)]
    width: Annotated[int, Field(ge=1, le=MAX_IMAGE_SIDE)]
    height: Annotated[int, Field(ge=1, le=MAX_IMAGE_SIDE)]

    @model_validator(mode="after")
    def bounded_pixels(self):
        if self.width * self.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image pixel limit exceeded")
        return self


class CharacterV1(DomainModel):
    schema_id: Literal["character"] = "character"
    schema_version: Literal["1"] = "1"
    subject_id: SubjectId
    revision: Revision
    bio: CharacterBio
    images: Annotated[list[CharacterImage], Field(min_length=1, max_length=6)]


class CharacterRef(DomainModel):
    subject_id: SubjectId
    revision: Revision
    digest: ImageDigest


class CharacterSaveReceipt(DomainModel):
    mutation_id: MutationId
    ref: CharacterRef


class _Mutation(DomainModel):
    payload_digest: ImageDigest
    receipt: CharacterSaveReceipt


class _Manifest(DomainModel):
    schema_version: Literal["1"] = "1"
    current: dict[SubjectId, CharacterRef] = Field(default_factory=dict)
    mutations: dict[MutationId, _Mutation] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_refs(self):
        refs = set()
        versions = set()
        for key, mutation in self.mutations.items():
            ref = mutation.receipt.ref
            version = (ref.subject_id, ref.revision)
            if key != mutation.receipt.mutation_id or version in versions:
                raise ValueError("Invalid mutation receipt history")
            versions.add(version)
            refs.add(ref)
        for key, ref in self.current.items():
            if key != ref.subject_id or ref not in refs:
                raise ValueError("Invalid current character ref")
        for ref in refs:
            current = self.current.get(ref.subject_id)
            if current is None or ref.revision > current.revision:
                raise ValueError("Invalid character history")
        if len(versions) != sum(ref.revision for ref in self.current.values()):
            raise ValueError("Incomplete character history")
        return self


class _SavePayload(DomainModel):
    bio: CharacterBio
    images: list[ImageDigest]
    mime_types: list[str]
    subject_id: SubjectId | None
    expected_revision: Revision | None
    mutation_id: MutationId


def _directories(path: Path, *, create: bool = False) -> None:
    for directory in (*reversed(path.parents), path):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            if not create:
                raise
            try:
                directory.mkdir()
            except FileExistsError:
                pass
            _sync_directory(directory.parent)
            info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("Managed directory must not be redirected")


def _read_file(path: Path, limit: int) -> bytes:
    _directories(path.parent)
    _check_file(path)
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        opened = os.fstat(source.fileno())
        _check_file(path)
        if not os.path.samestat(before, opened) or not os.path.samestat(opened, path.lstat()):
            raise ValueError("Managed file was replaced")
        body = source.read(limit + 1)
    if len(body) > limit:
        raise ValueError("Managed file exceeds size limit")
    return body


def _publish(path: Path, body: bytes, *, replace: bool = False) -> None:
    _directories(path.parent, create=True)
    try:
        existing = _read_file(path, MAX_JSON_BYTES if path.suffix == ".json" else MAX_IMAGE_BYTES)
    except FileNotFoundError:
        pass
    else:
        if not replace:
            if existing != body:
                raise ValueError("Conflicting immutable bytes")
            return
    descriptor, name = tempfile.mkstemp(prefix=".character-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(body)
            temporary.flush()
            os.fsync(temporary.fileno())
        if replace:
            os.replace(name, path)
        else:
            # All publishers hold the library lock; the checked destination cannot
            # exist. Rename avoids a crash leaving a temporary hardlink to the object.
            os.rename(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    _sync_directory(path.parent)


def _safe_image(raw: ImageInput) -> tuple[CharacterImage, bytes]:
    format, _ = _FORMATS[raw.mime_type]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw.data), formats=[format]) as image:
                if (image.width > MAX_IMAGE_SIDE or image.height > MAX_IMAGE_SIDE
                        or image.width * image.height > MAX_IMAGE_PIXELS):
                    raise ValueError("Image dimension/pixel limit exceeded")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Animated images are unsupported")
                image.verify()
            with Image.open(BytesIO(raw.data), formats=[format]) as image:
                image.load()  # verify alone does not decode the pixel data.
                oriented = ImageOps.exif_transpose(image)
                mode = "RGB" if format == "JPEG" else "RGBA"
                with oriented, oriented.convert(mode) as pixels, Image.new(mode, oriented.size) as clean:
                    clean.paste(pixels)  # A new image carries no uploaded metadata.
                    output = BytesIO()
                    options = {"quality": 90} if format == "JPEG" else {"lossless": True} if format == "WEBP" else {}
                    clean.save(output, format=format, **options)
                    body = output.getvalue()
                    metadata = CharacterImage(digest=sha256_digest(body), mime_type=raw.mime_type,
                                              byte_length=len(body), width=clean.width, height=clean.height)
                    return metadata, body
    except (OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValueError("Invalid or unsafe image") from error


class CharacterRepository:
    def __init__(self, root: Path | str):
        path = Path(root)
        if ".." in path.parts:
            raise ValueError("Library root must not contain traversal")
        self.root = path.absolute()
        try:
            _directories(self.root)
        except FileNotFoundError:
            pass

    def _manifest(self) -> _Manifest:
        try:
            body = _read_file(self.root / "manifest.json", MAX_JSON_BYTES)
        except FileNotFoundError:
            # Never treat a missing manifest in an initialized library as empty.
            if (self.root / "revisions").exists() or (self.root / "images").exists():
                raise ValueError("Library manifest is missing; recovery required")
            return _Manifest()
        manifest = parse_json_model(body, _Manifest)
        if canonical_json(manifest) != body:
            raise ValueError("Noncanonical library manifest")
        return manifest

    def _revision_path(self, ref: CharacterRef) -> Path:
        return self.root / "revisions" / ref.subject_id / f"{ref.revision}-{ref.digest[7:]}.json"

    def _image_path(self, image: CharacterImage) -> Path:
        return self.root / "images" / f"{image.digest[7:]}.{_FORMATS[image.mime_type][1]}"

    def _read_exact(self, ref: CharacterRef, manifest: _Manifest) -> CharacterV1:
        # Only committed revisions are readable; orphan objects grant no authority.
        if not any(m.receipt.ref == ref for m in manifest.mutations.values()):
            raise FileNotFoundError("Character revision is not committed")
        body = _read_file(self._revision_path(ref), MAX_JSON_BYTES)
        if sha256_digest(body) != ref.digest:
            raise ValueError("Character integrity check failed")
        card = parse_json_model(body, CharacterV1)
        if (card.subject_id, card.revision) != (ref.subject_id, ref.revision) or canonical_json(card) != body:
            raise ValueError("Character revision identity mismatch")
        return card

    def list(self) -> list[tuple[CharacterRef, CharacterV1]]:
        manifest = self._manifest()
        return [(ref, self._read_exact(ref, manifest)) for _, ref in sorted(manifest.current.items())]

    def read_current(self, subject_id: str) -> tuple[CharacterRef, CharacterV1]:
        # Reuse ref validation without accepting a filesystem path as identity.
        CharacterRef(subject_id=subject_id, revision=1, digest="sha256:" + "0" * 64)
        manifest = self._manifest()
        ref = manifest.current.get(subject_id)
        if ref is None:
            raise FileNotFoundError("Unknown character")
        return ref, self._read_exact(ref, manifest)

    def read_exact(self, ref: CharacterRef) -> CharacterV1:
        ref = CharacterRef.model_validate(ref)
        return self._read_exact(ref, self._manifest())

    def read_image(self, ref: CharacterRef, image_digest: str) -> tuple[CharacterImage, bytes]:
        CharacterRef(subject_id=ref.subject_id, revision=ref.revision, digest=image_digest)
        card = self.read_exact(ref)
        image = next((image for image in card.images if image.digest == image_digest), None)
        if image is None:
            raise FileNotFoundError("Image does not belong to this character revision")
        body = _read_file(self._image_path(image), MAX_IMAGE_BYTES)
        if len(body) != image.byte_length or sha256_digest(body) != image.digest:
            raise ValueError("Image integrity check failed")
        return image, body

    def save(self, bio: CharacterBio, images: Sequence[ImageInput], *, mutation_id: str,
             subject_id: str | None = None, expected_revision: int | None = None) -> CharacterSaveReceipt:
        """Create without subject/revision; update requires both. Busy lock raises OSError.

        Replay compares the validated bio, ordered raw image bytes/MIMEs and update
        target/OCC revision, before decoding or checking current OCC. It returns the
        original receipt without restoring an older current binding.
        """
        bio = CharacterBio.model_validate(bio)
        if not isinstance(images, Sequence) or not 1 <= len(images) <= 6:
            raise ValueError("A character requires 1-6 images")
        images = tuple(images)
        for raw in images:
            if (not isinstance(raw, ImageInput) or type(raw.data) is not bytes
                    or not 1 <= len(raw.data) <= MAX_IMAGE_BYTES or type(raw.mime_type) is not str
                    or raw.mime_type not in _FORMATS):
                raise ValueError("Invalid image input or byte limit")
        payload = _SavePayload(bio=bio, images=[sha256_digest(raw.data) for raw in images],
                               mime_types=[raw.mime_type for raw in images], mutation_id=mutation_id,
                               subject_id=subject_id, expected_revision=expected_revision)
        if (subject_id is None) != (expected_revision is None):
            raise ValueError("Update requires subject_id and expected_revision; create requires neither")
        payload_digest = sha256_digest(canonical_json(payload))
        # Validate before touching disk. Replay still hashes original uploads, not
        # encoder output which can change with a future Pillow upgrade.
        manifest = self._manifest()
        prior = manifest.mutations.get(mutation_id)
        if prior is not None:
            if prior.payload_digest != payload_digest:
                raise ValueError("Conflicting mutation payload")
            self.read_exact(prior.receipt.ref)
            return prior.receipt
        safe_images = [_safe_image(raw) for raw in images]
        _directories(self.root, create=True)
        # ponytail: one library lock and 1 MiB manifest; split only at that ceiling.
        with own_data_root(self.root):
            manifest = self._manifest()
            prior = manifest.mutations.get(mutation_id)
            if prior is not None:
                if prior.payload_digest != payload_digest:
                    raise ValueError("Conflicting mutation payload")
                self._read_exact(prior.receipt.ref, manifest)
                return prior.receipt
            if subject_id is None:
                subject_id, revision = "character-" + uuid4().hex, 1
            else:
                current = manifest.current.get(subject_id)
                if current is None:
                    raise FileNotFoundError("Unknown character")
                if current.revision != expected_revision:
                    raise ValueError("Stale expected_revision")
                self._read_exact(current, manifest)
                revision = current.revision + 1
            card = CharacterV1(subject_id=subject_id, revision=revision, bio=bio,
                               images=[metadata for metadata, _ in safe_images])
            body = canonical_json(card)
            ref = CharacterRef(subject_id=subject_id, revision=revision, digest=sha256_digest(body))
            receipt = CharacterSaveReceipt(mutation_id=mutation_id, ref=ref)
            manifest.current[subject_id] = ref
            manifest.mutations[mutation_id] = _Mutation(payload_digest=payload_digest, receipt=receipt)
            committed = canonical_json(manifest)  # Capacity/validation failure before publication.
            # An empty committed manifest distinguishes interrupted first saves
            # from a missing/corrupted manifest in an established library.
            manifest_path = self.root / "manifest.json"
            if not manifest_path.exists():
                _publish(manifest_path, canonical_json(_Manifest()))
            for metadata, data in safe_images:
                _publish(self._image_path(metadata), data)
            _publish(self._revision_path(ref), body)
            _publish(manifest_path, committed, replace=True)
            return receipt
