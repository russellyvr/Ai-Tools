"""Deterministic chunker: ExtractionBundle text -> rag/chunks.jsonl.

Sliding window over each page's text with target/overlap character sizes and
whitespace-boundary preference (the cut point backs up to the last whitespace
inside the final 20% of the window when one exists). Identical inputs and
configuration always produce byte-identical chunks.jsonl.

``chunk_id`` is content-derived::

    sha256(canonical_json({schema_version, source_sha256, extraction_sha256,
                           channel, page_number, char_start, char_end,
                           text_sha256, chunk_config_sha256}))

so any consumer can independently re-derive and verify every chunk.
"""
from __future__ import annotations

import json
from pathlib import Path

from evidence_ingest import TOOL_VERSION
from evidence_ingest.custody import CustodyLog
from evidence_ingest.gates import code_tree_sha256
from evidence_ingest.hashing import canonical_json, sha256_of_json, sha256_of_text
from evidence_ingest.scan import load_config, load_records, save_config
from evidence_ingest.schemas import SCHEMA_VERSION, RagChunk


def chunk_config_sha(target: int, overlap: int) -> str:
    return sha256_of_json({"schema_version": SCHEMA_VERSION,
                           "target": target, "overlap": overlap})


def window_spans(text: str, target: int, overlap: int) -> list[tuple[int, int]]:
    """Compute deterministic (char_start, char_end) spans for one text."""
    if target <= 0:
        raise ValueError("target must be positive")
    if overlap < 0 or overlap >= target:
        raise ValueError("overlap must satisfy 0 <= overlap < target")
    n = len(text)
    if n == 0:
        return []
    spans: list[tuple[int, int]] = []
    start = 0
    while start < n:
        end = min(start + target, n)
        if end < n:
            # whitespace-boundary preference inside the final 20% of window
            floor = end - max(1, target // 5)
            cut = -1
            for i in range(end - 1, max(start, floor) - 1, -1):
                if text[i].isspace():
                    cut = i + 1
                    break
            if cut > start:
                end = cut
        spans.append((start, end))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return spans


def make_chunk_id(source_sha256: str, extraction_sha256: str, channel: str,
                  page_number: int | None, char_start: int, char_end: int,
                  text_sha256: str, cfg_sha: str) -> str:
    return sha256_of_json({
        "schema_version": SCHEMA_VERSION,
        "source_sha256": source_sha256,
        "extraction_sha256": extraction_sha256,
        "channel": channel,
        "page_number": page_number,
        "char_start": char_start,
        "char_end": char_end,
        "text_sha256": text_sha256,
        "chunk_config_sha256": cfg_sha,
    })


def run_chunk(work: Path, custody: CustodyLog,
              target: int | None = None, overlap: int | None = None) -> int:
    """Chunk every extraction bundle; emit canonical-JSONL chunks (LF)."""
    from evidence_ingest.extract import load_bundle

    work = Path(work)
    config = load_config(work)
    if target is not None:
        config.chunk_target = target
    if overlap is not None:
        config.chunk_overlap = overlap
    save_config(work, config)

    run_id = json.loads((work / "run.json").read_text(encoding="utf-8"))["run_id"]
    cfg_sha = chunk_config_sha(config.chunk_target, config.chunk_overlap)
    code_sha = code_tree_sha256()

    records = load_records(work)
    (work / "rag").mkdir(exist_ok=True)
    out_path = work / "rag" / "chunks.jsonl"
    n = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for sha in sorted(records):
            rec = records[sha]
            bundle, extraction_sha = load_bundle(work, sha)
            relpaths = sorted(o.relpath for o in rec.occurrences)
            for page in bundle.pages:
                text = page.text
                for char_start, char_end in window_spans(
                        text, config.chunk_target, config.chunk_overlap):
                    piece = text[char_start:char_end]
                    if not piece.strip():
                        continue
                    b_start = len(text[:char_start].encode("utf-8"))
                    b_end = b_start + len(piece.encode("utf-8"))
                    t_sha = sha256_of_text(piece)
                    chunk = RagChunk(
                        chunk_id=make_chunk_id(sha, extraction_sha, bundle.channel,
                                               page.page_number, char_start,
                                               char_end, t_sha, cfg_sha),
                        source_sha256=sha,
                        source_relpaths=relpaths,
                        media_type=rec.media_type,
                        channel=bundle.channel,
                        page_number=page.page_number,
                        char_start=char_start,
                        char_end=char_end,
                        utf8_byte_start=b_start,
                        utf8_byte_end=b_end,
                        text=piece,
                        text_sha256=t_sha,
                        extraction_sha256=extraction_sha,
                        chunk_config_sha256=cfg_sha,
                        tool_version=TOOL_VERSION,
                        code_tree_sha256=code_sha,
                        run_id=run_id,
                    )
                    out.write(canonical_json(chunk.model_dump()) + "\n")
                    n += 1
    custody.append("chunk_completed", {
        "chunks": n, "chunk_config_sha256": cfg_sha,
        "target": config.chunk_target, "overlap": config.chunk_overlap})
    return n
