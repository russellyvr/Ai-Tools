"""Human-readable extraction report + machine audit report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_ingest import TOOL_VERSION
from evidence_ingest.gates import code_tree_sha256
from evidence_ingest.scan import load_config, load_records
from evidence_ingest.schemas import DropRecord


def _load_drops(work: Path) -> list[DropRecord]:
    drops = []
    p = work / "ledger" / "drops.jsonl"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    drops.append(DropRecord.model_validate(json.loads(line)))
    return drops


def _csv_guard(value: str) -> str:
    """Neutralize CSV-injection: prefix formula-trigger leading chars."""
    if value and value[0] in "=+-@\t\r":
        return "'" + value
    return value


def build_reports(work: Path, dest: Path) -> None:
    """Write _extraction-report.md, _audit.json and _index.csv into dest."""
    import csv

    work, dest = Path(work), Path(dest)
    records = load_records(work)
    drops = _load_drops(work)
    config = load_config(work)
    run = json.loads((work / "run.json").read_text(encoding="utf-8"))

    chunk_counts: dict[str, int] = {}
    chunks_path = work / "rag" / "chunks.jsonl"
    total_chunks = 0
    if chunks_path.exists():
        with open(chunks_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    sha = json.loads(line)["source_sha256"]
                    chunk_counts[sha] = chunk_counts.get(sha, 0) + 1
                    total_chunks += 1

    ocr_status = {}
    osp = work / "ledger" / "ocr-status.json"
    if osp.exists():
        ocr_status = json.loads(osp.read_text(encoding="utf-8")).get("status", {})

    # _index.csv
    with open(dest / "_index.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["sha256", "media_type", "size_bytes", "occurrence_count",
                    "first_relpath", "vault_relpath", "ocr_status", "chunk_count"])
        for sha in sorted(records):
            r = records[sha]
            w.writerow([sha, r.media_type, r.size_bytes, len(r.occurrences),
                        _csv_guard(sorted(o.relpath for o in r.occurrences)[0]),
                        f"evidence/sha256/{sha[:2]}/{sha}",
                        ocr_status.get(sha, "n/a"),
                        chunk_counts.get(sha, 0)])

    by_type: dict[str, int] = {}
    for r in records.values():
        by_type[r.media_type] = by_type.get(r.media_type, 0) + 1
    by_reason: dict[str, int] = {}
    for d in drops:
        by_reason[d.reason_code] = by_reason.get(d.reason_code, 0) + 1

    audit = {
        "tool_version": TOOL_VERSION,
        "code_tree_sha256": code_tree_sha256(),
        "run": run,
        "config": config.model_dump(),
        "unique_evidence_objects": len(records),
        "total_occurrences": sum(len(r.occurrences) for r in records.values()),
        "dropped": len(drops),
        "drops_by_reason": by_reason,
        "media_types": by_type,
        "rag_chunks": total_chunks,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (dest / "_audit.json").write_text(
        json.dumps(audit, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Evidence extraction report",
        "",
        f"- Generated: {audit['generated_utc']}",
        f"- Tool: {TOOL_VERSION}",
        f"- Code tree: `{audit['code_tree_sha256']}`",
        f"- Run id: `{run['run_id']}`",
        f"- Input: `{run['input_realpath']}`",
        "",
        "## Totals",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Unique evidence objects | {audit['unique_evidence_objects']} |",
        f"| Source occurrences | {audit['total_occurrences']} |",
        f"| Dropped inputs | {audit['dropped']} |",
        f"| RAG chunks | {total_chunks} |",
        "",
        "## Media types",
        "",
        "| Type | Count |",
        "|---|---|",
    ]
    for t in sorted(by_type):
        lines.append(f"| {t} | {by_type[t]} |")
    lines += ["", "## Dropped inputs by reason", ""]
    if by_reason:
        lines += ["| Reason | Count |", "|---|---|"]
        for rc in sorted(by_reason):
            lines.append(f"| {rc} | {by_reason[rc]} |")
        lines += ["", "Every dropped input is enumerated in `_custody.jsonl` "
                      "(`source_dropped` events) with its reason code."]
    else:
        lines.append("None — every walked input file was accepted.")
    lines += [
        "",
        "## Doctrine",
        "",
        "No LLM was used anywhere in this evidentiary pipeline. Every artifact "
        "in this corpus is deterministically re-derivable from the verbatim "
        "source bytes stored under `evidence/sha256/`. Run "
        "`python -m evidence_ingest verify --output <this folder>` to re-verify.",
        "",
    ]
    (dest / "_extraction-report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
