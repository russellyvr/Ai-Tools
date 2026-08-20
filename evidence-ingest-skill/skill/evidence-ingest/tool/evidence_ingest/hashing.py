"""Hashing primitives: streaming sha256, canonical JSON, manifest writer.

Canonical JSON is the byte-level contract used for every derived hash
(custody events, chunk ids, gate files): ``json.dumps`` with sorted keys,
no whitespace padding, ``ensure_ascii=False``, UTF-8 encoded.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

CHUNK_BYTES = 1 << 20  # 1 MiB streaming reads


def fs_str(path) -> str:
    """Return a filesystem-safe absolute path string.

    On Windows this applies the ``\\\\?\\`` extended-length prefix so that
    reserved device names (CON, NUL.txt, ...) resolve to the actual files on
    disk instead of console devices, and long paths work. Elsewhere it is a
    plain absolute path.
    """
    s = os.path.abspath(str(path))
    if sys.platform == "win32" and not s.startswith("\\\\?\\"):
        if s.startswith("\\\\"):
            return "\\\\?\\UNC\\" + s[2:]
        return "\\\\?\\" + s
    return s


def sha256_of(path: Path) -> str:
    """Stream-hash a file in 1 MiB chunks; never loads the file into memory."""
    h = hashlib.sha256()
    with open(fs_str(path), "rb") as f:
        for block in iter(lambda: f.read(CHUNK_BYTES), b""):
            h.update(block)
    return h.hexdigest()


def sha256_of_fileobj(f) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: f.read(CHUNK_BYTES), b""):
        h.update(block)
    return h.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj) -> str:
    """Deterministic JSON serialization (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")


def sha256_of_json(obj) -> str:
    return sha256_of_bytes(canonical_json_bytes(obj))


def write_manifest(root: Path, manifest_path: Path, exclude_names: set[str] | None = None) -> int:
    """Write ``sha256<TAB>relpath`` lines (POSIX relpaths, sorted, LF).

    ``exclude_names`` are top-level file names to skip (the manifest itself
    and mutable custody log are excluded so the manifest is stable).
    Returns number of entries written.
    """
    exclude = exclude_names or set()
    entries: list[tuple[str, str]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel in exclude:
            continue
        entries.append((sha256_of(p), rel))
    entries.sort(key=lambda e: e[1])
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        for digest, rel in entries:
            f.write(f"{digest}\t{rel}\n")
    return len(entries)


def read_manifest(manifest_path: Path) -> dict[str, str]:
    """Return {relpath: sha256} from a manifest file."""
    out: dict[str, str] = {}
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            digest, _, rel = line.partition("\t")
            out[rel] = digest
    return out
