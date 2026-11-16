"""Read an intern's uploaded source archive (a .zip) well enough to review it.

The client asks that an intern upload the project's source as a zip in
addition to the GitHub link, and that the automated review check both. This
service produces the zip half of that: a bounded digest the reviewer model
reads alongside the repository snapshot, so it can judge whether the archive
is really the same project the intern named and linked.

Safety is the whole point of keeping this separate from the image-attachment
path:

* **Nothing is ever extracted to disk and nothing is executed.** Only the
  listing and a bounded sample of text files are read, entirely in memory, so
  a crafted path (`../../etc/...`) has nothing to escape into — there is no
  write. Unsafe names are still rejected outright rather than merely ignored.
* **Totals are checked before any entry is read.** A zip bomb is caught from
  its own metadata (declared uncompressed sizes and per-file compression
  ratio), so the host is never asked to inflate it.
"""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, List

from app.services.github_repo import (
    IGNORED_DIRS,
    MANIFEST_FILES,
    SOURCE_EXTENSIONS,
)

logger = logging.getLogger("uvicorn.error")

# Compressed upload ceiling. Enforced again at the endpoint, but a service
# that reads untrusted archives states its own limit rather than trusting the
# caller to have checked.
MAX_ARCHIVE_BYTES = 60 * 1024 * 1024
# The sum of declared uncompressed sizes. Past this the archive is refused
# before a single byte is decompressed — the zip-bomb guard.
MAX_TOTAL_UNCOMPRESSED = 400 * 1024 * 1024
MAX_ENTRIES = 12_000
# A single member that inflates more than this, and is large, is treated as a
# bomb even when the running total is still under the ceiling.
MAX_COMPRESSION_RATIO = 200
MAX_SINGLE_UNCOMPRESSED = 8 * 1024 * 1024

MAX_READ_FILE_BYTES = 24_000
MAX_SOURCE_FILES = 16
MAX_TREE = 400

TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs"}


class ArchiveError(RuntimeError):
    """The archive could not be read, or was refused as unsafe."""


@dataclass
class ArchiveSnapshot:
    """Everything the review service is given about an uploaded archive."""

    filename: str
    entry_count: int
    total_uncompressed: int
    top_level: List[str]
    tree: List[str]
    has_tests: bool
    has_readme: bool
    has_dockerfile: bool
    manifests: Dict[str, str] = field(default_factory=dict)
    source_samples: Dict[str, str] = field(default_factory=dict)

    def as_facts(self) -> Dict[str, Any]:
        """The subset stored on the enrollment, so an admin can see what the
        review was based on without re-opening the archive."""
        return {
            "filename": self.filename,
            "entry_count": self.entry_count,
            "total_uncompressed_bytes": self.total_uncompressed,
            "top_level": self.top_level,
            "file_count": len(self.tree),
            "has_tests": self.has_tests,
            "has_readme": self.has_readme,
            "has_dockerfile": self.has_dockerfile,
            "manifests_read": sorted(self.manifests.keys()),
            "source_samples_read": sorted(self.source_samples.keys()),
        }


def _is_unsafe(name: str) -> bool:
    """A member name that must never be trusted as a path.

    Nothing is written, so this cannot cause traversal here; it is rejected so
    an archive that was built to escape — absolute paths, drive letters, `..`
    segments — is refused loudly rather than reviewed as if it were normal.
    """
    raw = name.replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute():
        return True
    # Windows drive or UNC prefix, which PurePosixPath does not treat as absolute.
    if len(raw) >= 2 and raw[1] == ":":
        return True
    return ".." in pure.parts


def _strip_prefix(names: List[str]) -> str:
    """A zip usually wraps everything in one top folder (``project-main/``).

    Return that single common first segment so paths read cleanly and match
    the repository tree; return ``""`` when there is no single wrapper.
    """
    firsts = {name.split("/", 1)[0] for name in names if "/" in name}
    roots_at_top = any("/" not in name for name in names)
    if len(firsts) == 1 and not roots_at_top:
        return next(iter(firsts)) + "/"
    return ""


def _rel(name: str, prefix: str) -> str:
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


def _in_ignored_dir(rel_path: str) -> bool:
    return any(part in IGNORED_DIRS for part in rel_path.split("/")[:-1])


def digest_archive(data: bytes, filename: str = "archive.zip") -> ArchiveSnapshot:
    """Validate an uploaded zip and read a bounded digest of it, in memory."""
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ArchiveError("The source archive is larger than 60 MB.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ArchiveError("That file is not a valid .zip archive.") from exc

    infos = [info for info in archive.infolist() if not info.is_dir()]
    if not infos:
        raise ArchiveError("The archive is empty.")
    if len(infos) > MAX_ENTRIES:
        raise ArchiveError(f"The archive has more than {MAX_ENTRIES} files.")

    # Guard pass — everything that must be true before any byte is read back.
    total = 0
    for info in infos:
        if _is_unsafe(info.filename):
            raise ArchiveError("The archive contains an unsafe file path.")
        total += info.file_size
        if total > MAX_TOTAL_UNCOMPRESSED:
            raise ArchiveError("The archive expands to more than 400 MB.")
        if (
            info.compress_size > 0
            and info.file_size > MAX_SINGLE_UNCOMPRESSED
            and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise ArchiveError("The archive has an abnormal compression ratio.")

    names = [info.filename for info in infos]
    prefix = _strip_prefix(names)

    rel_paths = sorted(_rel(name, prefix) for name in names)
    tree = [path for path in rel_paths if path][:MAX_TREE]

    has_readme = any(
        path.lower().startswith("readme") and "/" not in path for path in rel_paths
    )
    has_dockerfile = any(
        path.split("/")[-1].lower() == "dockerfile" for path in rel_paths
    )
    has_tests = any(
        any(part.lower() in TEST_DIR_NAMES for part in path.split("/")[:-1])
        or path.split("/")[-1].lower().startswith(("test_", "test."))
        or path.split("/")[-1].lower().endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js"))
        for path in rel_paths
    )

    manifests: Dict[str, str] = {}
    source_samples: Dict[str, str] = {}

    def _read(info: zipfile.ZipInfo) -> str:
        with archive.open(info) as handle:
            # Bounded read: never pull more than the sample size into memory,
            # regardless of the member's declared size.
            raw = handle.read(MAX_READ_FILE_BYTES)
        return raw.decode("utf-8", "replace")

    by_name = {info.filename: info for info in infos}

    # Manifests first — they say what the project is and how it runs.
    for name in names:
        rel = _rel(name, prefix)
        if _in_ignored_dir(rel):
            continue
        if rel.split("/")[-1].lower() in MANIFEST_FILES:
            manifests[rel] = _read(by_name[name])

    # Then a shallow-first sample of real source files.
    source_candidates = sorted(
        (
            _rel(name, prefix)
            for name in names
            if not _in_ignored_dir(_rel(name, prefix))
            and PurePosixPath(_rel(name, prefix)).suffix.lower() in SOURCE_EXTENSIONS
        ),
        key=lambda path: (path.count("/"), path),
    )
    name_by_rel = {_rel(name, prefix): name for name in names}
    for rel in source_candidates[:MAX_SOURCE_FILES]:
        source_samples[rel] = _read(by_name[name_by_rel[rel]])

    return ArchiveSnapshot(
        filename=filename,
        entry_count=len(infos),
        total_uncompressed=total,
        top_level=sorted({path.split("/")[0] for path in rel_paths if path})[:40],
        tree=tree,
        has_tests=has_tests,
        has_readme=has_readme,
        has_dockerfile=has_dockerfile,
        manifests=manifests,
        source_samples=source_samples,
    )
