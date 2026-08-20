"""Validation gate: re-derive everything from bytes; fail closed.

Checks (all must pass before ``_VALIDATED.ok`` is written):
  1. Custody chain re-verification (every event hash + link).
  2. Source/vault byte identity: every accepted occurrence's source file is
     re-hashed and must equal the recorded sha; every vault object is
     re-hashed and must equal its content address.
  3. Occurrence reconciliation: a fresh walk of the input tree must equal
     accepted occurrences + drops EXACTLY (no unexplained additions or
     disappearances).
  4. Path confinement: every artifact path realpath-resolves under the work
     dir; vault addresses match the sha-derived layout.
  5. Bundle re-validation with pydantic ``extra="forbid"`` and re-parse
     equivalence for native-text channels.
  6. Chunk re-derivation on a deterministic sample: offsets, text hash and
     chunk_id are recomputed from the bundle text.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from evidence_ingest.custody import CustodyError, verify_chain
from evidence_ingest.gates import VALIDATED_GATE, write_gate
from evidence_ingest.hashing import fs_str, sha256_of, sha256_of_bytes, sha256_of_json, sha256_of_text
from evidence_ingest.chunk import chunk_config_sha, make_chunk_id
from evidence_ingest.scan import load_config, load_records, vault_relpath_for, walk_regular_candidates
from evidence_ingest.schemas import DropRecord, ExtractionBundle, RagChunk

CHUNK_SAMPLE_MAX = 2000


class ValidationFailure(Exception):
    """Raised with the list of failures; callers map it to exit code 2."""

    def __init__(self, failures: list[str]):
        super().__init__(f"{len(failures)} validation failure(s)")
        self.failures = failures


def _confined(path: Path, root: Path) -> bool:
    try:
        rp = Path(os.path.realpath(path))
        return rp == root or str(rp).startswith(str(root) + os.sep)
    except OSError:
        return False


def run_validate(input_dir: Path, work: Path) -> dict:
    """Run every check; write _VALIDATED.ok only on a full pass."""
    input_dir = Path(input_dir).resolve()
    work = Path(work).resolve()
    # single-file input: occurrences resolve against the file's parent
    source_base = input_dir.parent if input_dir.is_file() else input_dir
    failures: list[str] = []
    stats: dict[str, int] = {}

    # 1. custody chain
    try:
        stats["custody_events"] = verify_chain(work / "_custody.jsonl")
    except CustodyError as e:
        raise  # custody violations escalate distinctly (exit 3)

    config = load_config(work)
    records = load_records(work)

    # ledgers
    occurrences: dict[str, list[dict]] = {}
    occ_path = work / "ledger" / "occurrences.jsonl"
    with open(occ_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                occurrences.setdefault(rec["sha256"], []).append(rec)
    drops: list[DropRecord] = []
    with open(work / "ledger" / "drops.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                drops.append(DropRecord.model_validate(json.loads(line)))

    # 2. byte identity: vault objects and source occurrences
    for sha in sorted(records):
        rec = records[sha]
        vault = work / rec.vault_relpath
        if rec.vault_relpath != vault_relpath_for(sha):
            failures.append(f"vault layout violation for {sha}")
        if not _confined(vault, work):
            failures.append(f"vault path escapes work dir: {vault}")
        if not vault.is_file():
            failures.append(f"vault object missing: {sha}")
            continue
        if sha256_of(vault) != sha:
            failures.append(f"TAMPER: vault bytes do not match address {sha}")
        for occ in rec.occurrences:
            parts = occ.relpath.split("/")
            if ".." in parts or any(p in ("", ".") for p in parts) or occ.relpath.startswith("/"):
                failures.append(f"occurrence path escapes input: {occ.relpath}")
                continue
            src = source_base / Path(*parts)
            if not os.path.isfile(fs_str(src)):
                failures.append(f"source disappeared since scan: {occ.relpath}")
                continue
            if sha256_of(src) != sha:
                failures.append(f"TAMPER: source bytes changed since scan: {occ.relpath}")

    # 3. occurrence reconciliation: fresh walk == accepted + dropped exactly
    walked = {rel for _, rel in walk_regular_candidates(input_dir)}
    accepted_paths = {o.relpath for r in records.values() for o in r.occurrences}
    dropped_paths = {d.relpath for d in drops}
    accounted = accepted_paths | dropped_paths
    for rel in sorted(walked - accounted):
        failures.append(f"unaccounted input file (appeared since scan?): {rel}")
    for rel in sorted(accounted - walked):
        failures.append(f"ledger references file no longer present: {rel}")
    if accepted_paths & dropped_paths:
        failures.append(f"paths both accepted and dropped: {sorted(accepted_paths & dropped_paths)[:5]}")
    # occurrences ledger must mirror records ledger
    rec_occs = {(sha, o.relpath) for sha, r in records.items() for o in r.occurrences}
    led_occs = {(sha, o["relpath"]) for sha, lst in occurrences.items() for o in lst}
    if rec_occs != led_occs:
        failures.append("occurrence ledger does not reconcile with records ledger")
    stats["inputs_walked"] = len(walked)
    stats["accepted_occurrences"] = len(accepted_paths)
    stats["dropped"] = len(dropped_paths)

    # 5. bundle re-validation (extra=forbid) + extraction re-derivation
    for sha in sorted(records):
        bpath = work / "extracted" / f"{sha}.bundle.json"
        if not bpath.is_file():
            failures.append(f"extraction bundle missing: {sha}")
            continue
        raw = bpath.read_bytes()
        try:
            bundle = ExtractionBundle.model_validate(json.loads(raw))
        except Exception as e:
            failures.append(f"SCHEMA: bundle rejected for {sha}: {type(e).__name__}")
            continue
        if bundle.source_sha256 != sha:
            failures.append(f"bundle source_sha256 mismatch for {sha}")
        # deterministic re-parse equivalence for native-text
        if bundle.channel == "native-text":
            from evidence_ingest.extract import _bundle_for
            re_bundle = _bundle_for(records[sha], work)
            if [p.text for p in re_bundle.pages] != [p.text for p in bundle.pages]:
                failures.append(f"re-parse text mismatch for {sha}")

    # 6. chunk re-derivation
    chunks_path = work / "rag" / "chunks.jsonl"
    n_chunks = 0
    if chunks_path.is_file():
        bundle_cache: dict[str, tuple[ExtractionBundle, str]] = {}
        with open(chunks_path, encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        stats["chunks"] = len(lines)
        step = max(1, len(lines) // CHUNK_SAMPLE_MAX)
        for i in range(0, len(lines), step):
            n_chunks += 1
            try:
                chunk = RagChunk.model_validate(json.loads(lines[i]))
            except Exception as e:
                failures.append(f"SCHEMA: chunk line {i + 1} rejected: {type(e).__name__}")
                continue
            if chunk.source_sha256 not in bundle_cache:
                from evidence_ingest.extract import load_bundle
                try:
                    bundle_cache[chunk.source_sha256] = load_bundle(work, chunk.source_sha256)
                except Exception:
                    failures.append(f"chunk references unknown bundle {chunk.source_sha256}")
                    continue
            bundle, extraction_sha = bundle_cache[chunk.source_sha256]
            if extraction_sha != chunk.extraction_sha256:
                failures.append(f"chunk {chunk.chunk_id[:12]}: extraction_sha256 mismatch")
                continue
            page_texts = {p.page_number: p.text for p in bundle.pages}
            text = page_texts.get(chunk.page_number)
            if text is None:
                failures.append(f"chunk {chunk.chunk_id[:12]}: page {chunk.page_number} missing")
                continue
            piece = text[chunk.char_start:chunk.char_end]
            if piece != chunk.text:
                failures.append(f"chunk {chunk.chunk_id[:12]}: offset text mismatch")
                continue
            if sha256_of_text(piece) != chunk.text_sha256:
                failures.append(f"chunk {chunk.chunk_id[:12]}: text_sha256 mismatch")
            cfg_sha = chunk_config_sha(config.chunk_target, config.chunk_overlap)
            derived = make_chunk_id(chunk.source_sha256, chunk.extraction_sha256,
                                    chunk.channel, chunk.page_number,
                                    chunk.char_start, chunk.char_end,
                                    chunk.text_sha256, cfg_sha)
            if derived != chunk.chunk_id:
                failures.append(f"chunk id not re-derivable: {chunk.chunk_id[:12]}")
    stats["chunks_verified"] = n_chunks

    # 4. path confinement over all work artifacts
    for p in work.rglob("*"):
        if not _confined(p, work):
            failures.append(f"artifact escapes work dir: {p}")

    if failures:
        raise ValidationFailure(failures)

    config_sha = sha256_of_json(config.model_dump())
    write_gate(work, VALIDATED_GATE, config_sha, extra={"stats": stats})
    return stats
