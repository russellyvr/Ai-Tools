"""Red-team selftest coordinator.

Runs five deterministic adversarial agents through the REAL pipeline code
(scan/ocr/extract/chunk/validate — the same functions the CLI calls) against
synthetic fixtures under ``<work>/_selftest``. Each agent plants traps whose
oracles must show neutralization, and controls that must flow through the
pipeline unharmed. The gate demands 100% of traps neutralized AND 100% of
controls accepted; a single miss exits 2 and no ``_SELFTEST.ok`` is written.

There is intentionally NO skip flag: merge refuses to run without a fresh
selftest gate bound to the current code tree.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from evidence_ingest import TOOL_VERSION
from evidence_ingest.custody import CustodyLog
from evidence_ingest.gates import SELFTEST_GATE, write_gate
from evidence_ingest.hashing import sha256_of_json
from evidence_ingest.ocr import NullOcr, run_ocr
from evidence_ingest.scan import run_scan
from evidence_ingest.schemas import RunConfig
from evidence_ingest.extract import run_extract
from evidence_ingest.chunk import run_chunk
from evidence_ingest.validate import ValidationFailure, run_validate

SELFTEST_SEED = 0x5EED_2026


@dataclass
class Check:
    kind: Literal["trap", "control"]
    name: str
    passed: bool
    detail: str = ""


@dataclass
class AgentContext:
    """Sandbox handed to each agent: fixture root + real-pipeline helpers."""

    root: Path
    checks: list[Check] = field(default_factory=list)

    def dirs(self, label: str) -> tuple[Path, Path]:
        inp = self.root / label / "input"
        work = self.root / label / "work"
        inp.mkdir(parents=True, exist_ok=True)
        work.mkdir(parents=True, exist_ok=True)
        return inp, work

    def pipeline(self, inp: Path, work: Path, max_file_bytes: int = 64 * 1024 * 1024,
                 target: int = 400, overlap: int = 50):
        """Run the real scan -> null-OCR -> extract -> chunk sequence."""
        custody = CustodyLog(work / "_custody.jsonl")
        config = RunConfig(max_file_bytes=max_file_bytes, chunk_target=target,
                           chunk_overlap=overlap, ocr_mode="none",
                           tool_version=TOOL_VERSION)
        result = run_scan(inp, work, config, custody, jobs=1)
        run_ocr(work, NullOcr(), custody)
        run_extract(work, custody)
        run_chunk(work, custody)
        return result, custody

    def validate_ok(self, inp: Path, work: Path) -> tuple[bool, str]:
        try:
            run_validate(inp, work)
            return True, "validate passed"
        except ValidationFailure as e:
            return False, "; ".join(e.failures[:4])

    def trap(self, name: str, neutralized: bool, detail: str = "") -> None:
        self.checks.append(Check("trap", name, neutralized, detail))

    def control(self, name: str, accepted: bool, detail: str = "") -> None:
        self.checks.append(Check("control", name, accepted, detail))


def _netguard_posture_checks(ctx: AgentContext) -> None:
    """Default-deny posture must survive the cloud-OCR exception code.

    Without allow_cloud_host() having been called, the Document AI endpoint
    hostname must be unresolvable AND unconnectable. This runs in-process
    against the installed guard; no packet ever leaves the machine.
    """
    import socket

    from evidence_ingest import netguard

    if not netguard.is_installed():
        netguard.install()
    host = "us-documentai.googleapis.com"
    pre_allowed = host in netguard.allowed_hostnames_snapshot()

    try:
        socket.getaddrinfo(host, 443)
        resolved_blocked = False
    except netguard.NetworkBlockedError:
        resolved_blocked = True
    ctx.trap("cloud-ocr-host-dns-blocked-by-default",
             resolved_blocked and not pre_allowed,
             "guarded getaddrinfo resolved the Document AI host without the exception")

    try:
        s = socket.socket()
        try:
            s.connect((host, 443))
        finally:
            s.close()
        connect_blocked = False
    except netguard.NetworkBlockedError:
        connect_blocked = True
    except OSError:
        connect_blocked = False  # guard let it reach the OS: posture broken
    ctx.trap("cloud-ocr-host-connect-blocked-by-default",
             connect_blocked and not pre_allowed,
             "guarded socket allowed a connection attempt to the Document AI host")


def run_selftest(work: Path) -> int:
    """Execute all agents; write _SELFTEST.ok only on a perfect score.

    Returns 0 on pass, 2 on any trap leak or control rejection.
    """
    from evidence_ingest.redteam import (
        bitrot, contortionist, doppelganger, inkwell, masquerade)

    work = Path(work).resolve()
    root = work / "_selftest"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    agents = [
        ("inkwell", inkwell.run),
        ("bitrot", bitrot.run),
        ("masquerade", masquerade.run),
        ("doppelganger", doppelganger.run),
        ("contortionist", contortionist.run),
    ]

    all_checks: list[tuple[str, Check]] = []

    guard_ctx = AgentContext(root=root / "netguard")
    guard_ctx.root.mkdir(exist_ok=True)
    _netguard_posture_checks(guard_ctx)
    for c in guard_ctx.checks:
        all_checks.append(("netguard", c))

    for name, fn in agents:
        ctx = AgentContext(root=root / name)
        ctx.root.mkdir(exist_ok=True)
        fn(ctx)
        for c in ctx.checks:
            all_checks.append((name, c))

    traps = [(a, c) for a, c in all_checks if c.kind == "trap"]
    controls = [(a, c) for a, c in all_checks if c.kind == "control"]
    trap_ok = sum(1 for _, c in traps if c.passed)
    ctrl_ok = sum(1 for _, c in controls if c.passed)

    print(f"selftest: {len(agents)} agents, {len(traps)} traps, {len(controls)} controls")
    for agent, c in all_checks:
        mark = "PASS" if c.passed else "FAIL"
        label = "neutralized" if c.kind == "trap" else "accepted"
        print(f"  [{mark}] {agent:14s} {c.kind:7s} {c.name}"
              + ("" if c.passed else f" -- NOT {label}: {c.detail}"))
    print(f"selftest: traps neutralized {trap_ok}/{len(traps)}, "
          f"controls accepted {ctrl_ok}/{len(controls)}")

    if trap_ok != len(traps) or ctrl_ok != len(controls):
        print("selftest: FAILED — gate withheld (fix the pipeline, not the trap)")
        return 2

    config_sha = sha256_of_json({"selftest_seed": SELFTEST_SEED,
                                 "tool_version": TOOL_VERSION})
    write_gate(work, SELFTEST_GATE, config_sha, extra={
        "agents": [a for a, _ in agents],
        "traps": len(traps), "controls": len(controls)})
    print(f"selftest: PASSED — {SELFTEST_GATE} written")
    return 0
