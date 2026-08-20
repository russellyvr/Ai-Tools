"""Self-improvement capture: deterministic issue harvesting from run ledgers.

DOCTRINE — this module only COLLECTS sanitized, machine-derived issue
records (drop reasons, parse warnings, gate anomalies) into
``<work>/_improve/issues.jsonl``. It never contains evidence text, never
mutates any evidentiary artifact, and never applies changes. Analysis,
clustering, and patch PROPOSALS happen in the LLM control plane (the
``/ingest`` skill); application of Ring-0 changes requires human approval,
after which the code-tree hash change stales every gate and forces the
selftest to re-pass.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_ingest import TOOL_VERSION
from evidence_ingest.gates import code_tree_sha256
from evidence_ingest.hashing import canonical_json, sha256_of_json


def _fingerprint(kind: str, key: str) -> str:
    return sha256_of_json({"kind": kind, "key": key})[:16]


def harvest_issues(work: Path) -> list[dict]:
    """Derive sanitized issue records from a run's ledgers. No evidence text
    is ever copied — only reason codes, counts, and media types."""
    work = Path(work)
    issues: list[dict] = []
    utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    common = {"utc": utc, "tool_version": TOOL_VERSION,
              "code_tree_sha256": code_tree_sha256()}

    drops_path = work / "ledger" / "drops.jsonl"
    if drops_path.is_file():
        by_reason: dict[str, int] = {}
        with open(drops_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    code = json.loads(line).get("reason_code", "UNKNOWN")
                    by_reason[code] = by_reason.get(code, 0) + 1
        for code, n in sorted(by_reason.items()):
            issues.append({**common, "kind": "drop", "reason_code": code,
                           "count": n,
                           "fingerprint": _fingerprint("drop", code)})

    ext_dir = work / "extracted"
    if ext_dir.is_dir():
        warn_counts: dict[tuple[str, str], int] = {}
        for bpath in sorted(ext_dir.glob("*.bundle.json")):
            b = json.loads(bpath.read_text(encoding="utf-8"))
            for w in b.get("parse_warnings", []):
                # keep only the stable warning class (text before ':')
                cls = w.split(":", 1)[0].strip()
                key = (b.get("media_type", "?"), cls)
                warn_counts[key] = warn_counts.get(key, 0) + 1
        for (media, cls), n in sorted(warn_counts.items()):
            issues.append({**common, "kind": "parse_warning",
                           "media_type": media, "warning_class": cls,
                           "count": n,
                           "fingerprint": _fingerprint("parse_warning",
                                                       f"{media}|{cls}")})
    return issues


def run_improve(work: Path) -> int:
    """Append harvested issues to _improve/issues.jsonl (dedup by
    fingerprint within this run's harvest); return count appended."""
    work = Path(work)
    issues = harvest_issues(work)
    out_dir = work / "_improve"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "issues.jsonl"
    seen: set[str] = set()
    if out.is_file():
        with open(out, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    seen.add(json.loads(line).get("fingerprint", ""))
    appended = 0
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for issue in issues:
            if issue["fingerprint"] in seen:
                continue
            f.write(canonical_json(issue) + "\n")
            appended += 1
    return appended
