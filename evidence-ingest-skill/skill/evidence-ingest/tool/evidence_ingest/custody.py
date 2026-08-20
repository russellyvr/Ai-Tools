"""Hash-chained chain-of-custody log (JSONL).

Each event is ``{sequence, utc, event, details, prev_sha256, event_hash}``
where ``event_hash = sha256(canonical_json(record minus event_hash))`` and
``prev_sha256`` is the previous record's ``event_hash`` (genesis uses 64
zeros). Any mutation, insertion, or deletion breaks the chain, which is
re-verified during ``validate`` and ``verify``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_ingest.hashing import canonical_json, sha256_of_bytes

GENESIS = "0" * 64


class CustodyError(Exception):
    """Raised when the custody chain fails verification."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class CustodyLog:
    """Append-only hash-chained JSONL custody log."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._sequence, self._prev = self._tail()

    def _tail(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        last = None
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if last is None:
            return 0, GENESIS
        rec = json.loads(last)
        return int(rec["sequence"]) + 1, rec["event_hash"]

    def append(self, event: str, details: dict) -> dict:
        """Append one event, extending the hash chain, and fsync-free flush."""
        record = {
            "sequence": self._sequence,
            "utc": _utc_now(),
            "event": event,
            "details": details,
            "prev_sha256": self._prev,
        }
        record["event_hash"] = sha256_of_bytes(canonical_json(record).encode("utf-8"))
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(canonical_json(record) + "\n")
        self._sequence += 1
        self._prev = record["event_hash"]
        return record


def verify_chain(path: Path) -> int:
    """Re-derive every event hash and link; return event count.

    Raises :class:`CustodyError` on any break (wrong hash, wrong link,
    non-monotonic sequence, malformed line).
    """
    if not path.exists():
        raise CustodyError(f"custody log missing: {path}")
    prev = GENESIS
    expected_seq = 0
    count = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise CustodyError(f"{path}:{lineno}: malformed JSON: {e}") from e
            claimed = rec.get("event_hash")
            body = {k: v for k, v in rec.items() if k != "event_hash"}
            derived = sha256_of_bytes(canonical_json(body).encode("utf-8"))
            if claimed != derived:
                raise CustodyError(f"{path}:{lineno}: event_hash mismatch (chain tampered)")
            if rec.get("prev_sha256") != prev:
                raise CustodyError(f"{path}:{lineno}: prev_sha256 link broken")
            if rec.get("sequence") != expected_seq:
                raise CustodyError(f"{path}:{lineno}: sequence gap (expected {expected_seq})")
            prev = claimed
            expected_seq += 1
            count += 1
    return count
