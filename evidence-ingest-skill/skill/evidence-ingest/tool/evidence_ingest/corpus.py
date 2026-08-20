"""Derived analytical corpus: published output -> Parquet + DuckDB + seal.

DOCTRINE — everything this module writes is a REBUILDABLE DERIVATIVE, never
evidence. The published output folder (vault objects, bundles, chunks.jsonl,
custody chains, manifest) remains the sole evidentiary authority; this module
only re-shapes it for analysis:

  * ``chunks.parquet``   — every RagChunk as a typed columnar table.
  * ``documents.parquet``— one row per evidence object (sha, media type,
                           occurrences, sizes).
  * ``corpus.duckdb``    — views over the Parquet files for SQL analysis.
  * ``seal.json``        — Merkle roots binding the derivatives to the
                           evidentiary layer: a chunks root (over sorted
                           chunk_ids, which are themselves content-derived),
                           a documents root (over sorted evidence shas), and
                           the manifest root (over sorted manifest lines).

Because Parquet bytes are NOT stable across pyarrow versions, the seal's
LOGICAL roots — not the physical Parquet file hashes — are the
non-repudiation anchors. ``corpus --check`` re-reads the Parquet files and
re-derives every root; any drift from seal.json is reported as a failure.

No network access is required or performed; the netguard posture is
unchanged. No LLM output enters this path.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_ingest import TOOL_VERSION
from evidence_ingest.gates import code_tree_sha256
from evidence_ingest.hashing import read_manifest, sha256_of_bytes
from evidence_ingest.schemas import RagChunk

SEAL_NAME = "seal.json"


def merkle_root(leaves: list[str]) -> str:
    """Binary Merkle root over hex-digest leaves (already sorted by caller).

    Leaf hashing is domain-separated from node hashing (0x00 / 0x01
    prefixes) so a leaf can never be replayed as an interior node.
    """
    if not leaves:
        return sha256_of_bytes(b"\x00empty")
    level = [hashlib.sha256(b"\x00" + bytes.fromhex(x)).digest() for x in leaves]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(hashlib.sha256(b"\x01" + a + b).digest())
        level = nxt
    return level[0].hex()


def _load_chunks(output: Path) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    path = output / "rag" / "chunks.jsonl"
    if not path.is_file():
        return chunks
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(RagChunk.model_validate(json.loads(line)))
    return chunks


def _load_records(output: Path) -> list[dict]:
    """Rebuild per-document rows from published bundles + evidence objects."""
    from evidence_ingest.schemas import ExtractionBundle

    rows: list[dict] = []
    ext_dir = output / "extracted"
    if not ext_dir.is_dir():
        return rows
    for bpath in sorted(ext_dir.glob("*.bundle.json")):
        bundle = ExtractionBundle.model_validate(
            json.loads(bpath.read_text(encoding="utf-8")))
        obj = output / "evidence" / "sha256" / bundle.source_sha256[:2] / bundle.source_sha256
        rows.append({
            "sha256": bundle.source_sha256,
            "media_type": bundle.media_type,
            "channel": bundle.channel,
            "size_bytes": obj.stat().st_size if obj.is_file() else None,
            "pages": len(bundle.pages),
            "parse_warnings": len(bundle.parse_warnings),
            "tables": len(bundle.tables_meta),
            "subject": bundle.subject,
            "ocr_raw_sha256": bundle.ocr_raw_sha256,
        })
    return rows


def compute_roots(output: Path) -> dict[str, str]:
    """Re-derive the three logical Merkle roots from the published corpus."""
    chunks = _load_chunks(output)
    chunk_root = merkle_root(sorted(c.chunk_id for c in chunks))
    docs = _load_records(output)
    doc_root = merkle_root(sorted(r["sha256"] for r in docs))
    manifest = read_manifest(output / "_MANIFEST.sha256")
    manifest_root = merkle_root(
        [sha256_of_bytes(f"{sha}\t{rel}".encode("utf-8"))
         for rel, sha in sorted(manifest.items())])
    return {"chunks_root": chunk_root, "documents_root": doc_root,
            "manifest_root": manifest_root,
            "chunks": str(len(chunks)), "documents": str(len(docs))}


def run_corpus(output: Path, derived: Path) -> dict:
    """Build derived Parquet + DuckDB artifacts and write seal.json."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    output = Path(output).resolve()
    derived = Path(derived).resolve()
    if not (output / "_MANIFEST.sha256").is_file():
        raise FileNotFoundError(
            f"{output} is not a published corpus (no _MANIFEST.sha256); run merge first")
    derived.mkdir(parents=True, exist_ok=True)

    chunks = _load_chunks(output)
    chunk_rows = [{
        "chunk_id": c.chunk_id,
        "source_sha256": c.source_sha256,
        "source_relpaths": c.source_relpaths,
        "media_type": c.media_type,
        "channel": c.channel,
        "page_number": c.page_number,
        "char_start": c.char_start,
        "char_end": c.char_end,
        "text": c.text,
        "text_sha256": c.text_sha256,
        "extraction_sha256": c.extraction_sha256,
        "run_id": c.run_id,
    } for c in chunks]
    if chunk_rows:
        pq.write_table(pa.Table.from_pylist(chunk_rows),
                       derived / "chunks.parquet")
    doc_rows = _load_records(output)
    if doc_rows:
        pq.write_table(pa.Table.from_pylist(doc_rows),
                       derived / "documents.parquet")

    db_path = derived / "corpus.duckdb"
    try:
        import duckdb
        if db_path.exists():
            db_path.unlink()
        con = duckdb.connect(str(db_path))
        try:
            def _q(p: Path) -> str:
                return str(p).replace("'", "''")
            if chunk_rows:
                con.execute("CREATE VIEW chunks AS SELECT * FROM "
                            f"read_parquet('{_q(derived / 'chunks.parquet')}')")
            if doc_rows:
                con.execute("CREATE VIEW documents AS SELECT * FROM "
                            f"read_parquet('{_q(derived / 'documents.parquet')}')")
        finally:
            con.close()
        duck = "built"
    except ImportError:
        duck = "skipped (duckdb not installed)"

    roots = compute_roots(output)
    seal = {
        **roots,
        "tool_version": TOOL_VERSION,
        "code_tree_sha256": code_tree_sha256(),
        "output": str(output),
        "utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }
    (derived / SEAL_NAME).write_text(
        json.dumps(seal, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"chunks": len(chunk_rows), "documents": len(doc_rows),
            "duckdb": duck, "seal": roots}


def check_corpus(output: Path, derived: Path) -> list[str]:
    """Re-derive every logical root and compare with seal.json; also verify
    the Parquet derivatives agree with the evidentiary JSONL (id-set and
    count parity). Returns a list of failures (empty = pass)."""
    output = Path(output).resolve()
    derived = Path(derived).resolve()
    failures: list[str] = []
    seal_path = derived / SEAL_NAME
    if not seal_path.is_file():
        return [f"seal missing: {seal_path}"]
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    try:
        roots = compute_roots(output)
    except Exception as e:
        # Fail closed: an unreadable/undecodable evidentiary layer is itself
        # a check failure (e.g. tampered chunks.jsonl rejected by pydantic).
        return [f"RE-DERIVATION FAILED: {type(e).__name__}: {e}"]
    for key in ("chunks_root", "documents_root", "manifest_root"):
        if seal.get(key) != roots[key]:
            failures.append(f"SEAL MISMATCH: {key} recorded {seal.get(key, '?')[:12]}... "
                            f"re-derived {roots[key][:12]}...")

    # Parquet <-> JSONL parity
    pq_path = derived / "chunks.parquet"
    if pq_path.is_file():
        import pyarrow.parquet as pq
        table = pq.read_table(pq_path, columns=["chunk_id", "text", "text_sha256"])
        ids_parquet = sorted(table.column("chunk_id").to_pylist())
        jsonl_chunks = _load_chunks(output)
        ids_jsonl = sorted(c.chunk_id for c in jsonl_chunks)
        if ids_parquet != ids_jsonl:
            failures.append(
                f"PARITY: chunks.parquet ids ({len(ids_parquet)}) differ from "
                f"chunks.jsonl ids ({len(ids_jsonl)})")
        else:
            from evidence_ingest.hashing import sha256_of_text
            for text, t_sha in zip(table.column("text").to_pylist(),
                                   table.column("text_sha256").to_pylist()):
                if sha256_of_text(text) != t_sha:
                    failures.append("PARITY: parquet chunk text does not match its text_sha256")
                    break
    return failures
