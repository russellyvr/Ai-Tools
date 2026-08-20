"""Intake stage: walk input, capture to content-addressed vault, account for everything.

Guarantees:
  * lstat-first: symlinks, reparse points, and non-regular files are never
    opened, only dropped with a reason code.
  * Source-changed-during-capture detection: fstat before + after the
    streaming copy, plus an independent re-hash of the vault copy.
  * Magic-byte classification with extension-consistency and structural
    (truncation / trailing-data) checks — mismatches are TAMPER_* drops.
  * Content-addressed dedup: identical bytes stored once under
    ``vault/sha256/<aa>/<sha>``; every source occurrence preserved in the
    occurrence ledger.
  * Fail-closed accounting: every walked file becomes either an accepted
    occurrence or a drop-ledger entry; validate reconciles the ledgers
    against a fresh walk.
"""
from __future__ import annotations

import json
import os
import stat as stat_mod
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from multiprocessing import get_context
from pathlib import Path

from evidence_ingest import TOOL_VERSION
from evidence_ingest.custody import CustodyLog
from evidence_ingest.hashing import (
    CHUNK_BYTES,
    canonical_json,
    fs_str,
    sha256_of,
    sha256_of_json,
)
from evidence_ingest.schemas import (
    REASON_COPY_MISMATCH,
    REASON_EMPTY,
    REASON_MAGIC_MISMATCH,
    REASON_NOT_REGULAR,
    REASON_REPARSE,
    REASON_SOURCE_CHANGED,
    REASON_SYMLINK,
    REASON_TOO_LARGE,
    REASON_TRAILING,
    REASON_TRUNCATED,
    DropRecord,
    EvidenceRecord,
    Occurrence,
    RunConfig,
)

_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

_EXT_EXPECTATION = {
    ".pdf": "pdf", ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg",
    ".tif": "tiff", ".tiff": "tiff", ".bmp": "bmp",
    ".eml": "eml", ".txt": "txt", ".md": "txt",
    ".csv": "csv",
    ".html": "html", ".htm": "html",
    ".docx": "docx", ".xlsx": "xlsx",
    ".doc": "doc", ".xls": "xls",
}

_BINARY_MAGICS = (
    (b"%PDF", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
    (b"BM", "bmp"),
    (b"PK\x03\x04", "zip"),                                  # OOXML (docx/xlsx)
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),            # legacy doc/xls (CFB)
)

# Sniff labels that denote structured binary content; text-y extensions
# (.txt/.md/.csv/.html/.htm/.eml) must never accept these.
_STRUCTURED_SNIFFS = ("pdf", "png", "jpeg", "tiff", "bmp", "zip", "ole")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def sniff_magic(head: bytes) -> str:
    """Classify content from leading bytes; deterministic, no library."""
    for magic, label in _BINARY_MAGICS:
        if head.startswith(magic):
            return label
    # email-ish: first line looks like an RFC5322 header or mbox From-line
    first_line = head.split(b"\n", 1)[0][:200]
    if first_line.startswith(b"From ") or _looks_like_header(first_line):
        return "eml"
    try:
        head.decode("utf-8")
        return "txt"
    except UnicodeDecodeError:
        return "other"


def _looks_like_header(line: bytes) -> bool:
    if b":" not in line:
        return False
    name = line.split(b":", 1)[0]
    return 0 < len(name) <= 64 and all(33 <= b <= 126 and b != 58 for b in name)


def structural_check(media: str, head: bytes, tail: bytes) -> str | None:
    """Detect truncation / appended-trailer tampering for structured formats.

    Returns a REASON_* code or None. Deterministic byte-level checks only.
    """
    if media == "pdf":
        idx = tail.rfind(b"%%EOF")
        if idx < 0:
            return REASON_TRUNCATED
        rest = tail[idx + 5:].strip(b" \t\r\n\x00")
        if rest:
            return REASON_TRAILING
    elif media == "png":
        idx = tail.rfind(b"IEND")
        if idx < 0:
            return REASON_TRUNCATED
        # IEND chunk = 4-byte type + 4-byte CRC; nothing may follow the CRC
        if tail[idx + 8:]:
            return REASON_TRAILING
    elif media == "jpeg":
        stripped = tail.rstrip(b"\x00")
        if not stripped.endswith(b"\xff\xd9"):
            return REASON_TRUNCATED if b"\xff\xd9" not in stripped else REASON_TRAILING
    elif media in ("docx", "xlsx", "zip"):
        # A well-formed ZIP archive ends with the End Of Central Directory
        # record (PK\x05\x06); its absence in the final bytes means the
        # archive was truncated. (A variable-length comment may follow the
        # EOCD, so trailing-data detection is not reliable for ZIP.)
        if b"PK\x05\x06" not in tail:
            return REASON_TRUNCATED
    return None


def classify(path_name: str, head: bytes, tail: bytes) -> tuple[str, str, str | None]:
    """Return (media_type, magic_label, drop_reason|None) for a captured file.

    Rules:
      * Binary magic wins. If the extension promises a different structured
        type, that is a TAMPER_MAGIC_MISMATCH drop.
      * ``.txt``/``.md``/``.csv`` accept any non-structured content (invalid
        UTF-8 is an extraction warning, not a drop) but reject binary-magic
        content.
      * ``.eml`` must look like an email or plain text.
      * ``.docx``/``.xlsx`` must be ZIP archives (OOXML); ``.doc``/``.xls``
        must be OLE compound files. Anything else is a mismatch drop.
    """
    ext = Path(path_name).suffix.lower()
    expected = _EXT_EXPECTATION.get(ext)
    sniffed = sniff_magic(head)

    if expected in ("pdf", "png", "jpeg", "tiff", "bmp"):
        if sniffed != expected:
            return sniffed, sniffed, REASON_MAGIC_MISMATCH
        reason = structural_check(expected, head, tail)
        return expected, sniffed, reason
    if expected in ("docx", "xlsx"):
        if sniffed != "zip":
            return sniffed, sniffed, REASON_MAGIC_MISMATCH
        reason = structural_check(expected, head, tail)
        return expected, sniffed, reason
    if expected in ("doc", "xls"):
        if sniffed != "ole":
            return sniffed, sniffed, REASON_MAGIC_MISMATCH
        return expected, sniffed, None
    if expected in ("txt", "csv", "html"):
        if sniffed in _STRUCTURED_SNIFFS:
            return sniffed, sniffed, REASON_MAGIC_MISMATCH
        return expected, sniffed, None
    if expected == "eml":
        if sniffed in _STRUCTURED_SNIFFS:
            return sniffed, sniffed, REASON_MAGIC_MISMATCH
        return "eml", sniffed, None
    # No extension expectation: trust the sniff.
    if sniffed in ("pdf", "png", "jpeg", "tiff", "bmp"):
        reason = structural_check(sniffed, head, tail)
        return sniffed, sniffed, reason
    if sniffed in ("zip", "ole"):
        # Structured container with no telling extension: preserved verbatim
        # as opaque bytes (no deterministic parser routing without the
        # extension's format promise).
        return "other", sniffed, None
    return sniffed if sniffed in ("eml", "txt") else "other", sniffed, None


def _is_reparse_point(st: os.stat_result) -> bool:
    if sys.platform != "win32":
        return False
    return bool(getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)


def vault_relpath_for(sha: str) -> str:
    return f"vault/sha256/{sha[:2]}/{sha}"


def _hash_worker(path_str: str) -> tuple[str, str]:
    """Top-level worker for spawn-based parallel pre-hashing."""
    return path_str, sha256_of(Path(path_str))


class ScanResult:
    def __init__(self):
        self.accepted_occurrences = 0
        self.dropped = 0
        self.unique_shas = 0


def walk_regular_candidates(input_path: Path):
    """Yield (abs_path, relpath_posix) for every directory entry that is a
    file-like name, without following symlinks. A single-file input yields
    exactly that file, with its bare name as the relpath."""
    input_dir = Path(input_path)
    if not input_dir.is_dir():
        # single-file input: exactly one candidate, never a directory walk
        yield input_dir, input_dir.name
        return
    for dirpath, dirnames, filenames in os.walk(input_dir, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            p = Path(dirpath) / name
            yield p, p.relative_to(input_dir).as_posix()


def run_scan(input_dir: Path, work: Path, config: RunConfig,
             custody: CustodyLog, jobs: int = 1) -> ScanResult:
    """Execute the intake stage. Never modifies the input tree. The input
    may be a directory (walked recursively) or a single file."""
    input_dir = Path(input_dir).resolve()
    work = Path(work).resolve()
    if not input_dir.is_dir() and not input_dir.is_file():
        raise FileNotFoundError(f"input path not found: {input_dir}")
    (work / "vault" / "sha256").mkdir(parents=True, exist_ok=True)
    (work / "ledger").mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    config_sha = sha256_of_json(config.model_dump())
    (work / "config.json").write_text(
        canonical_json(config.model_dump()) + "\n", encoding="utf-8")
    (work / "run.json").write_text(json.dumps({
        "run_id": run_id,
        "input_realpath": str(input_dir),
        "started_utc": _utc_now(),
        "tool_version": TOOL_VERSION,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    custody.append("scan_started", {
        "input": str(input_dir), "run_id": run_id, "config_sha256": config_sha})

    records: dict[str, EvidenceRecord] = {}
    drops: list[DropRecord] = []
    result = ScanResult()

    candidates = list(walk_regular_candidates(input_dir))

    if jobs > 1:
        # Parallel pre-hash pass (pure function, spawn context). The
        # authoritative hash is still the in-line streaming hash below.
        ctx = get_context("spawn")
        with ProcessPoolExecutor(max_workers=jobs, mp_context=ctx) as pool:
            list(pool.map(_hash_worker, [str(p) for p, _ in candidates]))

    tmp_counter = 0
    for abs_path, rel in candidates:
        drop = _capture_one(abs_path, rel, work, config, records, drops, tmp_counter)
        tmp_counter += 1
        if drop is not None:
            drops.append(drop)
            result.dropped += 1
            custody.append("source_dropped", {
                "relpath": rel, "reason_code": drop.reason_code, "detail": drop.detail})
        else:
            result.accepted_occurrences += 1

    result.unique_shas = len(records)

    with open(work / "ledger" / "occurrences.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for sha in sorted(records):
            for occ in records[sha].occurrences:
                f.write(canonical_json({"sha256": sha, **occ.model_dump()}) + "\n")
    with open(work / "ledger" / "drops.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for d in drops:
            f.write(canonical_json(d.model_dump()) + "\n")
    with open(work / "ledger" / "records.json", "w", encoding="utf-8", newline="\n") as f:
        f.write(canonical_json({sha: r.model_dump() for sha, r in sorted(records.items())}) + "\n")

    for sha in sorted(records):
        custody.append("source_captured", {
            "sha256": sha,
            "media_type": records[sha].media_type,
            "occurrences": [o.relpath for o in records[sha].occurrences],
        })
    custody.append("scan_completed", {
        "accepted_occurrences": result.accepted_occurrences,
        "dropped": result.dropped,
        "unique_shas": result.unique_shas,
    })
    return result


def _capture_one(abs_path: Path, rel: str, work: Path, config: RunConfig,
                 records: dict[str, EvidenceRecord], drops: list[DropRecord],
                 tmp_n: int) -> DropRecord | None:
    """Capture a single source file into the vault; return a DropRecord to
    reject it, or None on acceptance (records updated in place)."""
    def drop(code: str, detail: str) -> DropRecord:
        return DropRecord(relpath=rel, reason_code=code, detail=detail, utc=_utc_now())

    try:
        st = os.lstat(fs_str(abs_path))
    except OSError as e:
        return drop(REASON_NOT_REGULAR, f"lstat failed: {e}")
    if stat_mod.S_ISLNK(st.st_mode):
        return drop(REASON_SYMLINK, "symlink rejected (evidence must be regular files)")
    if _is_reparse_point(st):
        return drop(REASON_REPARSE, "reparse point rejected")
    if not stat_mod.S_ISREG(st.st_mode):
        return drop(REASON_NOT_REGULAR, f"mode={oct(st.st_mode)}")
    if st.st_size == 0:
        return drop(REASON_EMPTY, "zero-byte file")
    if st.st_size > config.max_file_bytes:
        return drop(REASON_TOO_LARGE,
                    f"{st.st_size} bytes exceeds cap {config.max_file_bytes}")

    tmp = work / "vault" / f".tmp-{os.getpid()}-{tmp_n}"
    try:
        import hashlib
        h = hashlib.sha256()
        with open(fs_str(abs_path), "rb") as src:
            before = os.fstat(src.fileno())
            with open(tmp, "wb") as dst:
                for block in iter(lambda: src.read(CHUNK_BYTES), b""):
                    h.update(block)
                    dst.write(block)
            after = os.fstat(src.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return drop(REASON_SOURCE_CHANGED,
                        "size/mtime changed during capture; evidence unstable")
        sha = h.hexdigest()
        # Independent re-hash of the copy: proves the vault bytes match what
        # was streamed, catching write-path corruption.
        if sha256_of(tmp) != sha:
            return drop(REASON_COPY_MISMATCH, "vault copy hash != stream hash")

        with open(tmp, "rb") as f:
            head = f.read(8192)
            if after.st_size > 8192:
                f.seek(max(0, after.st_size - 8192))
                tail = f.read(8192)
            else:
                tail = head[:after.st_size]
        media, magic_label, reason = classify(rel, head, tail)
        if reason is not None:
            return drop(reason, f"declared={Path(rel).suffix.lower() or '(none)'} sniffed={magic_label}")

        occ = Occurrence(
            relpath=rel, size_bytes=after.st_size,
            mtime_utc=datetime.fromtimestamp(after.st_mtime, tz=timezone.utc)
            .isoformat(timespec="microseconds"))
        if sha in records:
            records[sha].occurrences.append(occ)
            return None
        final = work / vault_relpath_for(sha)
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            if sha256_of(final) != sha:
                return drop(REASON_COPY_MISMATCH,
                            "existing vault object does not match its address")
        else:
            os.replace(tmp, final)
        records[sha] = EvidenceRecord(
            sha256=sha, size_bytes=after.st_size, media_type=media,
            magic_label=magic_label, vault_relpath=vault_relpath_for(sha),
            occurrences=[occ], captured_utc=_utc_now())
        return None
    except OSError as e:
        return drop(REASON_NOT_REGULAR, f"capture I/O failure: {e}")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def load_records(work: Path) -> dict[str, EvidenceRecord]:
    data = json.loads((work / "ledger" / "records.json").read_text(encoding="utf-8"))
    return {sha: EvidenceRecord.model_validate(rec) for sha, rec in data.items()}


def load_config(work: Path) -> RunConfig:
    return RunConfig.model_validate(
        json.loads((work / "config.json").read_text(encoding="utf-8")))


def save_config(work: Path, config: RunConfig) -> None:
    (work / "config.json").write_text(
        canonical_json(config.model_dump()) + "\n", encoding="utf-8")
