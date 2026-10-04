import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

from backend.characters import (
    CharacterBio, CharacterRef, CharacterRepository, CharacterV1, ImageInput,
    MAX_IMAGE_BYTES, MAX_IMAGE_PIXELS, MAX_IMAGE_SIDE,
)
from backend.domain import canonical_json, sha256_digest
from backend.ownership import own_data_root


def image_input(format="PNG", color="red", size=(24, 32), **options):
    output = BytesIO()
    with Image.new("RGB", size, color) as image:
        image.save(output, format=format, **options)
    return ImageInput(output.getvalue(), {"PNG": "image/png", "JPEG": "image/jpeg",
                                         "WEBP": "image/webp", "GIF": "image/gif"}[format])


class CharacterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel characters ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "characters"
        self.repo = CharacterRepository(self.root)
        self.bio = CharacterBio(name="Лея", age="young adult", gender="woman", vibe="warm")
        self.image = image_input()

    def create(self, mutation_id="create"):
        return self.repo.save(self.bio, [self.image], mutation_id=mutation_id)

    def revision_path(self, ref):
        return self.root / "revisions" / ref.subject_id / f"{ref.revision}-{ref.digest[7:]}.json"

    def image_path(self, ref):
        image = self.repo.read_exact(ref).images[0]
        suffix = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[image.mime_type]
        return self.root / "images" / f"{image.digest[7:]}.{suffix}"

    def test_empty_reads_do_not_create_library(self):
        self.assertEqual(self.repo.list(), [])
        self.assertFalse(self.root.exists())
        with self.assertRaises(FileNotFoundError):
            self.repo.read_current("character-" + "0" * 32)
        self.assertFalse(self.root.exists())

    def test_create_reopen_exact_json_and_safe_image_read(self):
        receipt = self.create()
        self.assertEqual(receipt.mutation_id, "create")
        self.assertRegex(receipt.ref.subject_id, r"^character-[0-9a-f]{32}$")
        self.assertEqual(receipt.ref.revision, 1)
        ref, card = CharacterRepository(self.root).read_current(receipt.ref.subject_id)
        self.assertEqual(ref, receipt.ref)
        self.assertEqual(card.bio, self.bio)
        self.assertEqual(card.schema_id, "character")
        self.assertEqual(card.schema_version, "1")
        self.assertEqual(card.revision, 1)
        self.assertEqual(card.subject_id, ref.subject_id)
        self.assertEqual(self.repo.list(), [(ref, card)])
        body = self.revision_path(ref).read_bytes()
        self.assertEqual(body, canonical_json(card))
        self.assertEqual(ref.digest, sha256_digest(body))
        self.assertEqual(set(json.loads(body)),
                         {"schema_id", "schema_version", "subject_id", "revision", "bio", "images"})
        with self.assertRaises(ValueError):
            CharacterV1.model_validate({**card.model_dump(), "schema_version": 1})
        metadata, data = self.repo.read_image(ref, card.images[0].digest)
        self.assertEqual(metadata, card.images[0])
        self.assertEqual(metadata.digest, "sha256:" + hashlib.sha256(data).hexdigest())
        self.assertEqual(metadata.byte_length, len(data))
        with Image.open(BytesIO(data)) as decoded:
            decoded.load()
            self.assertEqual(decoded.size, (24, 32))

    def test_edit_occ_immutable_history_and_restart_replay(self):
        first = self.create()
        original = self.revision_path(first.ref).read_bytes()
        changed = CharacterBio(name="Leia renamed", vibe="cool")
        second_image = image_input(color="blue")
        for expected in (None, 0, 2, True):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                self.repo.save(changed, [second_image], mutation_id="edit",
                               subject_id=first.ref.subject_id, expected_revision=expected)
        second = self.repo.save(changed, [second_image], mutation_id="edit",
                                subject_id=first.ref.subject_id, expected_revision=1)
        self.assertEqual(second.ref.subject_id, first.ref.subject_id)
        self.assertEqual(second.ref.revision, 2)
        reopened = CharacterRepository(self.root)
        self.assertEqual(reopened.save(self.bio, [self.image], mutation_id="create"), first)
        self.assertEqual(reopened.save(changed, [second_image], mutation_id="edit",
                                       subject_id=first.ref.subject_id, expected_revision=1), second)
        self.assertEqual(reopened.read_current(first.ref.subject_id)[0], second.ref)
        self.assertEqual(reopened.read_exact(first.ref).bio, self.bio)
        self.assertEqual(self.revision_path(first.ref).read_bytes(), original)
        self.assertEqual(reopened.read_image(first.ref, reopened.read_exact(first.ref).images[0].digest)[0],
                         reopened.read_exact(first.ref).images[0])
        with self.assertRaisesRegex(ValueError, "revision"):
            reopened.save(self.bio, [self.image], mutation_id="stale",
                          subject_id=first.ref.subject_id, expected_revision=1)
        with self.assertRaises(FileNotFoundError):
            reopened.save(self.bio, [self.image], mutation_id="unknown",
                          subject_id="character-" + "0" * 32, expected_revision=1)

    def test_mutation_conflicts_cover_payload_and_target(self):
        first = self.create()
        for bio, images, kwargs in (
            (CharacterBio(name="different"), [self.image], {}),
            (self.bio, [image_input(color="blue")], {}),
            (self.bio, [self.image, self.image], {}),
            (self.bio, [ImageInput(self.image.data, "image/jpeg")], {}),
            (self.bio, [self.image], {"subject_id": first.ref.subject_id, "expected_revision": 1}),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "mutation"):
                self.repo.save(bio, images, mutation_id="create", **kwargs)
        self.assertEqual(self.repo.read_current(first.ref.subject_id)[0], first.ref)

    def test_idempotency_survives_a_fresh_process(self):
        first = self.create()
        child = """
import sys
from pathlib import Path
from backend.characters import CharacterRepository, CharacterBio, ImageInput
receipt = CharacterRepository(Path(sys.argv[1])).save(
    CharacterBio.model_validate_json(sys.argv[2]),
    [ImageInput(bytes.fromhex(sys.argv[3]), 'image/png')], mutation_id='create')
print(receipt.model_dump_json())
"""
        result = subprocess.run([sys.executable, "-c", child, str(self.root),
                                 self.bio.model_dump_json(), self.image.data.hex()],
                                capture_output=True, text=True, timeout=15,
                                cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), first.model_dump(mode="json"))

    def test_bio_and_save_validation(self):
        for fields in ({"name": ""}, {"name": "   "}, {"name": "x" * 201},
                       {"name": "x", "age": 42}, {"name": "x", "age": "x" * 81},
                       {"name": "x", "gender": "x" * 81}, {"name": "x", "vibe": "x" * 4097},
                       {"name": "x", "audio": []}, {"name": "\ud800"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                CharacterBio.model_validate(fields)
        for images in ([], [self.image] * 7):
            with self.assertRaises(ValueError):
                self.repo.save(self.bio, images, mutation_id="invalid-count")
        for raw in (ImageInput(b"", "image/png"),
                    ImageInput(bytearray(self.image.data), "image/png"),  # type: ignore[arg-type]
                    ImageInput(self.image.data, [])):  # type: ignore[arg-type]
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.repo.save(self.bio, [raw], mutation_id="invalid-type")
        with self.assertRaises(ValueError):
            self.repo.save(self.bio, [self.image], mutation_id="", expected_revision=1)
        with self.assertRaises(ValueError):
            self.repo.save(self.bio, [self.image], mutation_id="invalid-create", expected_revision=1)
        self.assertFalse(self.root.exists())

    def test_supported_images_strip_metadata_trailing_bytes_and_apply_orientation(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "private data")
        exif = Image.Exif()
        exif[274] = 6  # Rotate clockwise before discarding metadata.
        for format, options in (("PNG", {"pnginfo": metadata}),
                                ("JPEG", {"exif": exif}), ("WEBP", {"exif": exif})):
            with self.subTest(format=format):
                raw = image_input(format, **options)
                raw = ImageInput(raw.data + b"<script>untrusted trailer</script>", raw.mime_type)
                receipt = self.repo.save(self.bio, [raw], mutation_id=format)
                card = self.repo.read_exact(receipt.ref)
                image, safe = self.repo.read_image(receipt.ref, card.images[0].digest)
                self.assertNotIn(b"private data", safe)
                self.assertNotIn(b"<script>", safe)
                with Image.open(BytesIO(safe)) as decoded:
                    decoded.load()
                    self.assertFalse(decoded.getexif())
                    self.assertNotIn("Comment", decoded.info)
                    self.assertEqual(decoded.format, format)
                    self.assertEqual(decoded.size, (24, 32) if format == "PNG" else (32, 24))
                self.assertEqual((image.width, image.height), decoded.size)

    def test_reject_fake_mismatched_truncated_animated_and_oversized_images(self):
        animation = BytesIO()
        with Image.new("RGB", (12, 12), "red") as a, Image.new("RGB", (12, 12), "blue") as b:
            a.save(animation, format="PNG", save_all=True, append_images=[b])
        cases = [ImageInput(b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/png"),
                 ImageInput(self.image.data, "image/svg+xml"),
                 ImageInput(self.image.data, "image/jpeg"),
                 ImageInput(self.image.data[:40], "image/png"),
                 ImageInput(b"x" * (MAX_IMAGE_BYTES + 1), "image/png"),
                 image_input("GIF"), ImageInput(animation.getvalue(), "image/png"),
                 image_input(size=(MAX_IMAGE_SIDE + 1, 1))]
        for raw in cases:
            with self.subTest(mime=raw.mime_type, length=len(raw.data)), self.assertRaises(ValueError):
                self.repo.save(self.bio, [self.image, raw], mutation_id="bad")
        # A cheap, valid file crossing the pixel budget; no forged header needed.
        with patch("backend.characters.MAX_IMAGE_PIXELS", 100):
            with self.assertRaises(ValueError):
                self.repo.save(self.bio, [self.image], mutation_id="pixels")
        self.assertGreater(MAX_IMAGE_PIXELS, 100)
        self.assertFalse(self.root.exists())

    def test_deduplicated_images_and_foreign_image_ref_rejected(self):
        first = self.create()
        second = self.create("another")
        self.assertNotEqual(first.ref.subject_id, second.ref.subject_id)
        self.assertEqual(self.repo.read_exact(first.ref).images, self.repo.read_exact(second.ref).images)
        self.assertEqual(len(list((self.root / "images").iterdir())), 1)
        with self.assertRaises(FileNotFoundError):
            self.repo.read_image(first.ref, "sha256:" + "0" * 64)

    def test_invalid_refs_cannot_traverse_paths(self):
        first = self.create()
        for subject in ("../outside", "character-" + "0" * 32 + "/..", "C:\\outside", "CON", ""):
            with self.subTest(subject=subject), self.assertRaises(ValueError):
                self.repo.read_current(subject)
            with self.assertRaises(ValueError):
                self.repo.save(self.bio, [self.image], mutation_id="path", subject_id=subject,
                               expected_revision=1)
        for digest in ("../outside", "sha256:" + "a" * 64 + "/..", "prefix-sha256:" + "a" * 64):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.repo.read_image(first.ref, digest)
            with self.assertRaises(ValueError):
                CharacterRef(subject_id=first.ref.subject_id, revision=1, digest=digest)
        with self.assertRaises(ValueError):
            CharacterRepository(self.root / ".." / "outside")

    def test_reads_recheck_redirected_managed_directories(self):
        first = self.create()
        card = self.repo.read_exact(first.ref)
        for directory in (self.root / "images", self.revision_path(first.ref).parent):
            with self.subTest(directory=directory):
                parked = self.root.parent / "parked"
                directory.rename(parked)
                if os.name == "nt":
                    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(directory), str(parked)],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    directory.symlink_to(parked, target_is_directory=True)
                try:
                    with self.assertRaises(ValueError):
                        self.repo.read_image(first.ref, card.images[0].digest)
                finally:
                    if os.name == "nt":
                        directory.rmdir()
                    else:
                        directory.unlink()
                    parked.rename(directory)

    def test_reject_redirected_root_and_managed_directories(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"untouched")
        # Windows junctions exercise redirection even without symlink privilege.
        for target in (self.root, self.root / "images", self.root / "revisions"):
            with self.subTest(target=target):
                if target != self.root:
                    self.root.mkdir(exist_ok=True)
                if os.name == "nt":
                    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(outside)],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    target.symlink_to(outside, target_is_directory=True)
                try:
                    with self.assertRaises(ValueError):
                        CharacterRepository(self.root).save(self.bio, [self.image], mutation_id="redirected")
                finally:
                    if os.name == "nt":
                        target.rmdir()
                    else:
                        target.unlink()
                self.assertEqual(set(outside.iterdir()), {sentinel})
                self.assertEqual(sentinel.read_bytes(), b"untouched")

    def test_hardlinked_managed_files_fail_closed(self):
        first = self.create()
        for path in (self.root / "manifest.json", self.revision_path(first.ref), self.image_path(first.ref)):
            with self.subTest(path=path):
                backup = path.read_bytes()
                outside = self.root.parent / "outside-file"
                outside.write_bytes(backup)
                path.unlink()
                os.link(outside, path)
                try:
                    with self.assertRaises(ValueError):
                        self.repo.read_image(first.ref, self.repo.read_exact(first.ref).images[0].digest)
                    with self.assertRaises(ValueError):
                        self.repo.save(self.bio, [self.image], mutation_id="linked",
                                       subject_id=first.ref.subject_id, expected_revision=1)
                    self.assertEqual(outside.read_bytes(), backup)
                finally:
                    path.unlink()
                    path.write_bytes(backup)
                    outside.unlink()

    def test_integrity_checks_and_no_orphan_exact_reads(self):
        first = self.create()
        revision = self.revision_path(first.ref)
        original = revision.read_bytes()
        revision.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.repo.read_exact(first.ref)
        revision.write_bytes(original)
        image = self.image_path(first.ref)
        image.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.repo.read_image(first.ref, self.repo.read_exact(first.ref).images[0].digest)
        forged = first.ref.model_copy(update={"digest": "sha256:" + "0" * 64})
        with self.assertRaises(FileNotFoundError):
            self.repo.read_exact(forged)

    def test_failed_manifest_commit_is_invisible_and_retryable(self):
        first = self.create()
        changed = CharacterBio(name="edited")
        manifest = (self.root / "manifest.json").read_bytes()
        original = self.revision_path(first.ref).read_bytes()
        with patch("backend.characters.os.replace", side_effect=OSError("disk failed")):
            with self.assertRaisesRegex(OSError, "disk failed"):
                self.repo.save(changed, [image_input(color="blue")], mutation_id="edit",
                               subject_id=first.ref.subject_id, expected_revision=1)
        self.assertEqual((self.root / "manifest.json").read_bytes(), manifest)
        self.assertEqual(self.revision_path(first.ref).read_bytes(), original)
        self.assertEqual(self.repo.read_current(first.ref.subject_id)[0], first.ref)
        orphan = next(path for path in self.revision_path(first.ref).parent.iterdir() if path != self.revision_path(first.ref))
        orphan_ref = CharacterRef(subject_id=first.ref.subject_id, revision=2,
                                  digest="sha256:" + orphan.stem.split("-", 1)[1])
        with self.assertRaises(FileNotFoundError):
            self.repo.read_exact(orphan_ref)
        self.assertFalse(list(self.root.rglob(".character-*")))
        second = CharacterRepository(self.root).save(changed, [image_input(color="blue")], mutation_id="edit",
                                                     subject_id=first.ref.subject_id, expected_revision=1)
        self.assertEqual(second.ref, orphan_ref)
        with patch("backend.characters.os.replace", side_effect=OSError("disk failed")):
            with self.assertRaises(OSError):
                self.create("failed-create")
        self.assertEqual(len(self.repo.list()), 1)
        self.assertEqual(self.repo.read_current(first.ref.subject_id)[0], second.ref)
        self.assertEqual(self.create("failed-create").ref.revision, 1)
        self.assertEqual(len(self.repo.list()), 2)

    def test_cross_process_writer_exclusion_and_release(self):
        first = self.create()
        child = """
import sys
from pathlib import Path
from backend.characters import CharacterRepository, CharacterBio, ImageInput
CharacterRepository(Path(sys.argv[1])).save(CharacterBio(name='child'),
    [ImageInput(bytes.fromhex(sys.argv[2]), 'image/png')], mutation_id='child')
"""
        command = [sys.executable, "-c", child, str(self.root), self.image.data.hex()]
        with own_data_root(self.root):
            refused = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                     cwd=Path(__file__).resolve().parents[1])
            self.assertNotEqual(refused.returncode, 0, refused.stderr)
            self.assertEqual(self.repo.read_current(first.ref.subject_id)[0], first.ref)
        acquired = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                  cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(acquired.returncode, 0, acquired.stderr)
        self.assertEqual(len(self.repo.list()), 2)

    def test_failed_first_save_is_empty_and_retryable_after_restart(self):
        with patch("backend.characters.os.replace", side_effect=OSError("disk failed")):
            with self.assertRaisesRegex(OSError, "disk failed"):
                self.create()
        reopened = CharacterRepository(self.root)
        self.assertEqual(reopened.list(), [])
        first = reopened.save(self.bio, [self.image], mutation_id="create")
        self.assertEqual(reopened.read_current(first.ref.subject_id)[0], first.ref)
        self.assertEqual(len(reopened.list()), 1)

    def test_missing_or_malformed_initialized_manifest_is_not_overwritten(self):
        first = self.create()
        path = self.root / "manifest.json"
        original = path.read_bytes()
        revision_body = self.revision_path(first.ref).read_bytes()
        for malformed in (None, b"{}", b"not json"):
            with self.subTest(malformed=malformed):
                if malformed is None:
                    path.unlink()
                else:
                    path.write_bytes(malformed)
                with self.assertRaises(ValueError):
                    self.repo.save(self.bio, [self.image], mutation_id="overwrite")
                self.assertEqual(self.revision_path(first.ref).read_bytes(), revision_body)
                if malformed is None:
                    self.assertFalse(path.exists())
                else:
                    self.assertEqual(path.read_bytes(), malformed)
                path.write_bytes(original)

    def test_process_death_before_and_after_commit_recovers_without_duplicate_save(self):
        child = """
import os, sys
from pathlib import Path
from backend import characters
publish = characters._publish
def crash(path, body, *, replace=False):
    publish(path, body, replace=replace)
    point = ('committed' if replace else 'initialized') if path.name == 'manifest.json' else (
        'images' if path.suffix == '.png' else 'revisions')
    if point == sys.argv[3]:
        os._exit(17)
characters._publish = crash
characters.CharacterRepository(Path(sys.argv[1])).save(characters.CharacterBio(name='child'),
    [characters.ImageInput(bytes.fromhex(sys.argv[2]), 'image/png')], mutation_id='child')
"""
        for point in ("initialized", "images", "revisions", "committed"):
            with self.subTest(point=point):
                root = self.root.parent / point
                result = subprocess.run([sys.executable, "-c", child, str(root), self.image.data.hex(), point],
                                        capture_output=True, text=True, timeout=15,
                                        cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(result.returncode, 17, result.stderr)
                reopened = CharacterRepository(root)
                previous = reopened.list()
                self.assertEqual(len(previous), 1 if point == "committed" else 0)
                receipt = reopened.save(CharacterBio(name="child"), [self.image], mutation_id="child")
                self.assertEqual(len(reopened.list()), 1)
                self.assertEqual(reopened.read_current(receipt.ref.subject_id)[0], receipt.ref)
                if previous:
                    self.assertEqual(receipt.ref, previous[0][0])


if __name__ == "__main__":
    unittest.main()
