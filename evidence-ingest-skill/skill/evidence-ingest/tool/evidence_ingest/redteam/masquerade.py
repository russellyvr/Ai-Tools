"""masquerade — metadata-spoofing agent.

Traps: spoofed display names over foreign addresses, lookalike domains,
conflicting Date headers, future and pre-epoch dates. Oracles: the pipeline
records every header verbatim as SOURCE-TAGGED UNTRUSTED metadata — it never
"corrects", trusts, or synthesizes identity or time; recipients are extracted
from the raw address part (not the display name), and impossible dates are
carried raw, never normalized into fabricated timestamps. Controls: a normal
email round-trips with faithful headers.
"""
from __future__ import annotations

import json

from evidence_ingest.hashing import sha256_of_bytes


def _eml(headers: list[tuple[str, str]], body: str) -> bytes:
    head = "".join(f"{k}: {v}\r\n" for k, v in headers)
    return (head + "\r\n" + body).encode("utf-8")


def run(ctx) -> None:
    inp, work = ctx.dirs("main")

    spoof = _eml([
        ("From", '"ceo@company.com" <mallory@evil.example>'),
        ("To", "victim@company.com"),
        ("Subject", "Wire transfer authorization"),
        ("Date", "Mon, 06 Jan 2031 10:00:00 +0000"),   # future date
        ("Message-ID", "<spoof-1@evil.example>"),
    ], "Please authorize immediately.\r\n")
    (inp / "spoof.eml").write_bytes(spoof)

    lookalike = _eml([
        ("From", "counsel@1awfirm.example"),           # digit-1 lookalike
        ("To", "client@company.com"),
        ("Subject", "Privileged and confidential"),
        ("Date", "Wed, 31 Dec 1969 23:59:59 +0000"),   # pre-epoch
    ], "Backdated correspondence.\r\n")
    (inp / "lookalike.eml").write_bytes(lookalike)

    conflict = _eml([
        ("From", "sender@company.com"),
        ("To", "recipient@company.com"),
        ("Subject", "Timeline anchor"),
        ("Date", "Tue, 01 Feb 2022 09:00:00 +0000"),
        ("Date", "Thu, 01 Feb 2018 09:00:00 +0000"),   # conflicting duplicate
    ], "Which date is real?\r\n")
    (inp / "conflict.eml").write_bytes(conflict)

    control = _eml([
        ("From", '"Jordan Yates" <jordan.yates@example.com>'),
        ("To", "priya.nair@example.com"),
        ("Cc", "records@example.com"),
        ("Subject", "Site inspection notes"),
        ("Date", "Mon, 04 Nov 2024 08:30:00 -0800"),
        ("Message-ID", "<control-1@example.com>"),
    ], "Notes attached from the November site inspection.\r\n")
    (inp / "control.eml").write_bytes(control)

    ctx.pipeline(inp, work)

    def bundle(data: bytes) -> dict | None:
        p = work / "extracted" / f"{sha256_of_bytes(data)}.bundle.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    b = bundle(spoof)
    ok = (b is not None
          and any(r["address"] == "mallory@evil.example" and r["role"] == "from"
                  for r in b["recipients"])
          and not any(r["address"] == "ceo@company.com" for r in b["recipients"]))
    ctx.trap("display-name-spoof-not-trusted", ok,
             "display-name address was treated as the sender identity")

    ok = (b is not None
          and b["date_raw"] == "Mon, 06 Jan 2031 10:00:00 +0000"
          and b["raw_headers"].get("Date") == ["Mon, 06 Jan 2031 10:00:00 +0000"])
    ctx.trap("future-date-carried-raw-untrusted", ok,
             "future date was normalized/synthesized instead of carried verbatim")

    b = bundle(lookalike)
    ok = (b is not None
          and any(r["address"] == "counsel@1awfirm.example" for r in b["recipients"])
          and b["date_raw"] == "Wed, 31 Dec 1969 23:59:59 +0000")
    ctx.trap("lookalike-domain-and-preepoch-verbatim", ok,
             "lookalike sender or pre-epoch date was altered")

    b = bundle(conflict)
    ok = (b is not None
          and b["raw_headers"].get("Date") == [
              "Tue, 01 Feb 2022 09:00:00 +0000",
              "Thu, 01 Feb 2018 09:00:00 +0000"])
    ctx.trap("conflicting-dates-both-preserved", ok,
             "duplicate Date headers collapsed — evidence of synthesis")

    b = bundle(control)
    ok = (b is not None
          and b["subject"] == "Site inspection notes"
          and any(r["address"] == "priya.nair@example.com" and r["role"] == "to"
                  for r in b["recipients"])
          and any(r["address"] == "jordan.yates@example.com" and r["role"] == "from"
                  for r in b["recipients"]))
    ctx.control("genuine-email-headers-faithful", ok)
    ok, detail = ctx.validate_ok(inp, work)
    ctx.control("corpus-validates", ok, detail)
