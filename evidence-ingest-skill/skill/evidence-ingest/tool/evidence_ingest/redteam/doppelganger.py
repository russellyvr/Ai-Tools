"""doppelganger — identity-collision & path-abuse agent.

Traps: exact duplicate content under different names, case-collision names
with different content, Unicode NFC/NFD twin filenames, Windows reserved
device names (CON, NUL.txt), traversal-looking names, and deep paths.
Oracles: dedup happens by content sha ONLY (occurrences preserved, never
merged by name), nothing is overwritten (distinct content keeps distinct
vault objects), and path confinement holds for every artifact.
"""
from __future__ import annotations

import json
import sys
import unicodedata

from evidence_ingest.hashing import sha256_of_bytes


def _write(path, data: bytes) -> bool:
    """Create a fixture file, using extended-length paths on Windows so even
    reserved device names become real files. Returns False if the platform
    refuses the name entirely."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        target = str(path)
        if sys.platform == "win32":
            target = "\\\\?\\" + target
        with open(target, "wb") as f:
            f.write(data)
        return True
    except OSError:
        return False


def run(ctx) -> None:
    inp, work = ctx.dirs("main")

    dup = b"Identical agreement text, executed in duplicate.\n" * 3
    _write(inp / "contracts" / "agreement-final.txt", dup)
    _write(inp / "archive" / "AGREEMENT_COPY.txt", dup)

    case_a = b"Version A of the memo: approve budget.\n"
    case_b = b"Version B of the memo: REJECT budget.\n"
    _write(inp / "a" / "Memo.txt", case_a)
    _write(inp / "b" / "memo.TXT", case_b)

    nfc_name = unicodedata.normalize("NFC", "café-notes.txt")
    nfd_name = unicodedata.normalize("NFD", "café-notes.txt")
    twin = b"Unicode twin content, one logical name, two encodings.\n"
    nfc_ok = _write(inp / "nfc" / nfc_name, twin)
    nfd_ok = _write(inp / "nfd" / nfd_name, twin)

    con_data = b"Reserved-name evidence body CON.\n"
    nul_data = b"Reserved-name evidence body NUL.\n"
    con_ok = _write(inp / "reserved" / "CON", con_data)
    nul_ok = _write(inp / "reserved" / "NUL.txt", nul_data)

    trav = b"Traversal-looking filename must not escape the vault.\n"
    _write(inp / "..%2f..%2fetc%2fpasswd.txt", trav)

    deep = inp
    for i in range(15):
        deep = deep / f"d{i:02d}"
    deep_data = b"Deeply nested evidence survives.\n"
    _write(deep / "leaf.txt", deep_data)

    control = b"Singleton control document.\n"
    _write(inp / "control.txt", control)

    html_twin = b"<html><body><p>Same markup, two extensions.</p></body></html>"
    _write(inp / "web" / "a.html", html_twin)
    _write(inp / "web" / "a.htm", html_twin)

    ctx.pipeline(inp, work)
    records = json.loads((work / "ledger" / "records.json").read_text(encoding="utf-8"))

    # Trap 1: exact dupes -> ONE vault object, BOTH occurrences preserved
    dup_sha = sha256_of_bytes(dup)
    rec = records.get(dup_sha)
    ok = (rec is not None and
          sorted(o["relpath"] for o in rec["occurrences"]) ==
          ["archive/AGREEMENT_COPY.txt", "contracts/agreement-final.txt"])
    ctx.trap("dedup-by-content-sha-only", ok,
             "duplicate content not unified or an occurrence was lost")

    # Trap 2: case-collision with DIFFERENT content -> no overwrite
    sha_a, sha_b = sha256_of_bytes(case_a), sha256_of_bytes(case_b)
    ok = (sha_a in records and sha_b in records
          and (work / records[sha_a]["vault_relpath"]).read_bytes() == case_a
          and (work / records[sha_b]["vault_relpath"]).read_bytes() == case_b)
    ctx.trap("case-collision-no-overwrite", ok,
             "one case-variant clobbered the other")

    # Trap 3: NFC/NFD twins dedup to one object with both occurrences
    twin_sha = sha256_of_bytes(twin)
    expected_occ = int(nfc_ok) + int(nfd_ok)
    rec = records.get(twin_sha)
    ok = rec is not None and len(rec["occurrences"]) == expected_occ
    ctx.trap("unicode-twin-names-content-addressed", ok,
             f"expected {expected_occ} occurrences for NFC/NFD twins")

    # Trap 4: reserved device names captured as real bytes (never devices)
    ok = True
    detail = ""
    for created, data, label in ((con_ok, con_data, "CON"), (nul_ok, nul_data, "NUL.txt")):
        if not created:
            continue  # platform refused the name at fixture time; nothing to defend
        sha = sha256_of_bytes(data)
        if sha not in records or (work / records[sha]["vault_relpath"]).read_bytes() != data:
            ok = False
            detail = f"reserved name {label} not captured verbatim"
    ctx.trap("reserved-device-names-neutralized", ok, detail)

    # Trap 5: traversal-looking name confined; vault path is sha-derived
    trav_sha = sha256_of_bytes(trav)
    rec = records.get(trav_sha)
    ok = (rec is not None
          and rec["vault_relpath"] == f"vault/sha256/{trav_sha[:2]}/{trav_sha}"
          and (work / rec["vault_relpath"]).resolve().is_relative_to(work.resolve()))
    ctx.trap("traversal-name-confined", ok,
             "traversal-looking name influenced the vault path")

    # Trap 6: .html/.htm twins dedupe to one object, one media type
    ht_sha = sha256_of_bytes(html_twin)
    rec = records.get(ht_sha)
    ok = (rec is not None and rec["media_type"] == "html"
          and sorted(o["relpath"] for o in rec["occurrences"]) ==
          ["web/a.htm", "web/a.html"])
    ctx.trap("html-htm-twins-content-addressed", ok,
             "html/htm twins not unified to one html-typed vault object")

    # Controls
    ctx.control("deep-path-accepted", sha256_of_bytes(deep_data) in records)
    ctx.control("control-file-accepted", sha256_of_bytes(control) in records)
    ok, detail = ctx.validate_ok(inp, work)
    ctx.control("corpus-validates", ok, detail)
