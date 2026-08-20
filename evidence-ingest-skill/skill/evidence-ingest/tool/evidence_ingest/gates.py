"""Stage gates bound to the exact code tree and configuration.

``_SELFTEST.ok`` and ``_VALIDATED.ok`` are JSON files containing
``code_tree_sha256`` (sha256 over sorted rel-path + bytes of every ``.py``
in this package), ``config_sha256``, and a UTC timestamp. ``require_gate``
refuses gates minted by a different code tree or config — editing one line
of pipeline code invalidates every prior gate, forcing re-attestation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SELFTEST_GATE = "_SELFTEST.ok"
VALIDATED_GATE = "_VALIDATED.ok"


class GateError(Exception):
    """Raised when a required gate is missing, malformed, or stale."""


def code_tree_sha256() -> str:
    """Hash every .py file in the package: sha256 over sorted (relpath, bytes)."""
    pkg_root = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(pkg_root.rglob("*.py"), key=lambda p: p.relative_to(pkg_root).as_posix()):
        rel = p.relative_to(pkg_root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(p.read_bytes())
        h.update(b"\x00")
    return h.hexdigest()


def write_gate(work: Path, name: str, config_sha256: str, extra: dict | None = None) -> Path:
    gate = {
        "gate": name,
        "code_tree_sha256": code_tree_sha256(),
        "config_sha256": config_sha256,
        "utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }
    if extra:
        gate.update(extra)
    path = Path(work) / name
    path.write_text(json.dumps(gate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def require_gate(work: Path, name: str, config_sha256: str | None = None) -> dict:
    """Load and verify a gate; raise GateError if absent or stale.

    Verifies code_tree binding always; verifies config binding when a
    config_sha256 is supplied.
    """
    path = Path(work) / name
    if not path.exists():
        raise GateError(f"required gate missing: {path} (run the earlier stage first)")
    try:
        gate = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise GateError(f"gate unreadable: {path}: {e}") from e
    current = code_tree_sha256()
    if gate.get("code_tree_sha256") != current:
        raise GateError(
            f"stale gate {name}: minted by code tree {gate.get('code_tree_sha256', '?')[:12]}..., "
            f"current is {current[:12]}... — re-run the gating stage"
        )
    if config_sha256 is not None and gate.get("config_sha256") != config_sha256:
        raise GateError(f"stale gate {name}: configuration changed since gate was minted")
    return gate


def clear_gate(work: Path, name: str) -> None:
    p = Path(work) / name
    if p.exists():
        p.unlink()
