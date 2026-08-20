"""argparse CLI for evidence-ingest.

Exit codes: 0 ok, 2 gate failure, 3 custody violation, 4 network-policy
violation, 5 environment unfit. The gated order is:

    selftest -> scan -> ocr -> extract -> chunk -> validate -> merge -> verify

``merge`` refuses to run without a fresh ``_SELFTEST.ok`` AND
``_VALIDATED.ok`` bound to the current code tree. There is deliberately no
flag anywhere that skips the selftest.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from evidence_ingest import (
    EXIT_CUSTODY, EXIT_ENVIRONMENT, EXIT_GATE, EXIT_NETWORK, EXIT_OK,
    TOOL_VERSION, netguard)
from evidence_ingest.custody import CustodyError, CustodyLog, verify_chain
from evidence_ingest.gates import (
    GateError, SELFTEST_GATE, VALIDATED_GATE, code_tree_sha256, require_gate)
from evidence_ingest.hashing import (
    canonical_json, read_manifest, sha256_of, sha256_of_bytes, sha256_of_json,
    sha256_of_text, write_manifest)
from evidence_ingest.locking import lock_tree, unlock_tree
from evidence_ingest.schemas import RagChunk, RunConfig


def _err(msg: str) -> None:
    print(f"evidence-ingest: {msg}", file=sys.stderr)


def _require_python() -> None:
    if sys.version_info < (3, 11):
        _err(f"Python 3.11+ required, running {sys.version.split()[0]}")
        raise SystemExit(EXIT_ENVIRONMENT)


# ---------------------------------------------------------------- commands

def cmd_selftest(args) -> int:
    from evidence_ingest.redteam.coordinator import run_selftest
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    return run_selftest(work)


def cmd_scan(args) -> int:
    from evidence_ingest.scan import run_scan
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    require_gate(work, SELFTEST_GATE)
    custody = CustodyLog(work / "_custody.jsonl")
    config = RunConfig(max_file_bytes=args.max_file_bytes,
                       tool_version=TOOL_VERSION)
    result = run_scan(Path(args.input), work, config, custody, jobs=args.jobs)
    print(f"scan: {result.accepted_occurrences} occurrences accepted, "
          f"{result.unique_shas} unique objects, {result.dropped} dropped")
    return EXIT_OK


def cmd_ocr(args) -> int:
    from evidence_ingest import ocr as ocr_mod
    from evidence_ingest.scan import load_config, save_config
    if args.google_docai and not args.allow_cloud_ocr:
        _err("refusing cloud OCR without explicit --allow-cloud-ocr "
             "(documented, audited exception to the closed-corpus rule)")
        return EXIT_NETWORK
    work = Path(args.work)
    require_gate(work, SELFTEST_GATE)
    custody = CustodyLog(work / "_custody.jsonl")
    config = load_config(work)

    if args.export_dir:
        n = ocr_mod.ocr_export(work, Path(args.export_dir), custody)
        config.ocr_mode = "enclave"
        save_config(work, config)
        print(f"ocr: exported {n} request(s) for folder-enclave OCR")
        return EXIT_OK
    if args.import_dir:
        n = ocr_mod.ocr_import(work, Path(args.import_dir), custody)
        config.ocr_mode = "enclave"
        save_config(work, config)
        print(f"ocr: imported {n} enclave response(s)")
        return EXIT_OK
    if args.no_ocr:
        status = ocr_mod.run_ocr(work, ocr_mod.NullOcr(), custody)
        config.ocr_mode = "none"
        save_config(work, config)
        n = sum(1 for v in status.values() if v == "ocr_unavailable")
        print(f"ocr: skipped (NullOcr); {n} record(s) marked ocr_unavailable")
        return EXIT_OK
    if args.google_docai:
        missing = [f for f, v in (("--project", args.project),
                                  ("--processor", args.processor),
                                  ("--token-file", args.token_file)) if not v]
        if missing:
            _err(f"--google-docai requires {' '.join(missing)}")
            return EXIT_GATE
        try:
            adapter = ocr_mod.GoogleDocAIAdapter(
                args.project, args.processor, args.location,
                Path(args.token_file), custody)
        except (ocr_mod.OcrError, OSError) as e:
            _err(f"google-docai setup failed: {e}")
            return EXIT_GATE
        status = ocr_mod.run_ocr(work, adapter, custody)
        config.ocr_mode = "google-docai"
        save_config(work, config)
        print(f"ocr: google-docai complete: "
              f"{sum(1 for v in status.values() if v == 'succeeded')} succeeded, "
              f"{sum(1 for v in status.values() if v == 'too_large_for_sync')} too large, "
              f"{sum(1 for v in status.values() if v == 'failed')} failed")
        return EXIT_OK
    if not args.endpoint:
        _err("ocr requires --no-ocr, --google-docai, --endpoint, --export, or --import")
        return EXIT_GATE
    if not args.allow_loopback_ocr:
        _err("refusing network OCR without explicit --allow-loopback-ocr")
        return EXIT_NETWORK
    adapter = ocr_mod.AzureReadContainer(args.endpoint, custody)
    status = ocr_mod.run_ocr(work, adapter, custody)
    config.ocr_mode = "azure-read"
    save_config(work, config)
    print(f"ocr: azure-read complete: "
          f"{sum(1 for v in status.values() if v == 'succeeded')} succeeded")
    return EXIT_OK


def cmd_extract(args) -> int:
    from evidence_ingest.extract import run_extract
    work = Path(args.work)
    require_gate(work, SELFTEST_GATE)
    custody = CustodyLog(work / "_custody.jsonl")
    n = run_extract(work, custody)
    print(f"extract: {n} bundle(s) written")
    return EXIT_OK


def cmd_chunk(args) -> int:
    from evidence_ingest.chunk import run_chunk
    work = Path(args.work)
    require_gate(work, SELFTEST_GATE)
    custody = CustodyLog(work / "_custody.jsonl")
    n = run_chunk(work, custody, target=args.target, overlap=args.overlap)
    print(f"chunk: {n} chunk(s) emitted")
    return EXIT_OK


def cmd_validate(args) -> int:
    from evidence_ingest.validate import ValidationFailure, run_validate
    work = Path(args.work)
    require_gate(work, SELFTEST_GATE)
    try:
        stats = run_validate(Path(args.input), work)
    except ValidationFailure as e:
        _err(f"VALIDATION FAILED ({len(e.failures)} failure(s)):")
        for f in e.failures[:50]:
            _err(f"  - {f}")
        return EXIT_GATE
    custody = CustodyLog(work / "_custody.jsonl")
    custody.append("validated", {"stats": stats})
    print(f"validate: PASSED {stats} — {VALIDATED_GATE} written")
    return EXIT_OK


def cmd_merge(args) -> int:
    return _merge(Path(args.work), Path(args.output))


def _merge(work: Path, output: Path) -> int:
    """Gated, append-only publication of the work corpus into the output.

    Refuses without fresh selftest+validated gates bound to the CURRENT code
    tree and config. Unlocks an existing corpus, appends (never overwrites
    differing bytes), regenerates manifests and reports, then re-locks in a
    ``finally`` so the corpus is never left unlocked.
    """
    from evidence_ingest.report import build_reports
    from evidence_ingest.scan import load_config, load_records

    work = work.resolve()
    require_gate(work, SELFTEST_GATE)
    config = load_config(work)
    require_gate(work, VALIDATED_GATE, sha256_of_json(config.model_dump()))
    verify_chain(work / "_custody.jsonl")

    records = load_records(work)
    run_id = json.loads((work / "run.json").read_text(encoding="utf-8"))["run_id"]

    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    if any(output.iterdir()):
        unlock_tree(output)
    try:
        for sub in ("evidence/sha256", "extracted", "ocr-raw", "rag", "custody-runs"):
            (output / sub).mkdir(parents=True, exist_ok=True)

        merged = 0
        for sha in sorted(records):
            rec = records[sha]
            src = work / rec.vault_relpath
            dst = output / "evidence" / "sha256" / sha[:2] / sha
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if sha256_of(dst) != sha:
                    raise GateError(f"output corpus corrupt: {dst} does not match its address")
            else:
                shutil.copyfile(src, dst)
                if sha256_of(dst) != sha:
                    raise GateError(f"copy verification failed for {sha}")
                merged += 1
            bsrc = work / "extracted" / f"{sha}.bundle.json"
            bdst = output / "extracted" / f"{sha}.bundle.json"
            if bdst.exists():
                if bdst.read_bytes() != bsrc.read_bytes():
                    raise GateError(
                        f"append-only violation: differing bundle already published for {sha}")
            else:
                shutil.copyfile(bsrc, bdst)
            osrc = work / "ocr-raw" / f"{sha}.json"
            if osrc.exists():
                odst = output / "ocr-raw" / f"{sha}.json"
                if odst.exists():
                    if odst.read_bytes() != osrc.read_bytes():
                        raise GateError(
                            f"append-only violation: differing ocr-raw already published for {sha}")
                else:
                    shutil.copyfile(osrc, odst)

        # chunks: append-only by chunk_id
        existing_ids: set[str] = set()
        chunks_out = output / "rag" / "chunks.jsonl"
        if chunks_out.exists():
            with open(chunks_out, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        existing_ids.add(json.loads(line)["chunk_id"])
        appended = 0
        with open(work / "rag" / "chunks.jsonl", encoding="utf-8") as src_f, \
                open(chunks_out, "a", encoding="utf-8", newline="\n") as out_f:
            for line in src_f:
                if line.strip() and json.loads(line)["chunk_id"] not in existing_ids:
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    appended += 1

        # custody: preserve the full run chain, then extend the corpus chain
        run_log = output / "custody-runs" / f"{run_id}.jsonl"
        run_log.write_bytes((work / "_custody.jsonl").read_bytes())
        corpus_custody = CustodyLog(output / "_custody.jsonl")
        corpus_custody.append("merge_completed", {
            "run_id": run_id,
            "code_tree_sha256": code_tree_sha256(),
            "tool_version": TOOL_VERSION,
            "evidence_objects_new": merged,
            "evidence_objects_total": len(records),
            "chunks_appended": appended,
            "run_custody_sha256": sha256_of(run_log),
        })

        build_reports(work, output)
        n = write_manifest(output, output / "_MANIFEST.sha256",
                           exclude_names={"_MANIFEST.sha256", "_custody.jsonl"})
        print(f"merge: {merged} new object(s), {appended} chunk(s) appended, "
              f"{n} manifest entries")
    finally:
        locked = lock_tree(output)
        print(f"merge: re-locked {locked} file(s) in output corpus")
    return EXIT_OK


def cmd_verify(args) -> int:
    """Full re-derivation of every hash in a published output corpus."""
    output = Path(args.output).resolve()
    failures: list[str] = []
    manifest_path = output / "_MANIFEST.sha256"
    if not manifest_path.exists():
        _err(f"no _MANIFEST.sha256 in {output}")
        return EXIT_GATE
    manifest = read_manifest(manifest_path)

    for rel, digest in sorted(manifest.items()):
        p = output / Path(*rel.split("/"))
        if not p.is_file():
            failures.append(f"manifest entry missing: {rel}")
        elif sha256_of(p) != digest:
            failures.append(f"TAMPER: hash mismatch: {rel}")
    listed = set(manifest) | {"_MANIFEST.sha256", "_custody.jsonl"}
    for p in sorted(output.rglob("*")):
        if p.is_file():
            rel = p.relative_to(output).as_posix()
            if rel not in listed:
                failures.append(f"unlisted file in corpus: {rel}")

    # evidence objects must match their content address
    for p in sorted((output / "evidence" / "sha256").rglob("*")):
        if p.is_file() and sha256_of(p) != p.name:
            failures.append(f"TAMPER: evidence object {p.name} bytes differ from address")

    # custody chains
    try:
        n = verify_chain(output / "_custody.jsonl")
        print(f"verify: corpus custody chain ok ({n} events)")
        for run_log in sorted((output / "custody-runs").glob("*.jsonl")):
            verify_chain(run_log)
    except CustodyError as e:
        _err(f"CUSTODY VIOLATION: {e}")
        return EXIT_CUSTODY

    # chunk-level re-derivation
    from evidence_ingest.chunk import make_chunk_id
    chunks_path = output / "rag" / "chunks.jsonl"
    n_chunks = 0
    if chunks_path.exists():
        with open(chunks_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                n_chunks += 1
                try:
                    c = RagChunk.model_validate(json.loads(line))
                except Exception as e:
                    failures.append(f"chunk line {i}: schema rejected ({type(e).__name__})")
                    continue
                if sha256_of_text(c.text) != c.text_sha256:
                    failures.append(f"chunk line {i}: text_sha256 mismatch")
                derived = make_chunk_id(c.source_sha256, c.extraction_sha256,
                                        c.channel, c.page_number, c.char_start,
                                        c.char_end, c.text_sha256,
                                        c.chunk_config_sha256)
                if derived != c.chunk_id:
                    failures.append(f"chunk line {i}: chunk_id not re-derivable")
                if not (output / "evidence" / "sha256" / c.source_sha256[:2]
                        / c.source_sha256).is_file():
                    failures.append(f"chunk line {i}: source evidence object missing")

    if failures:
        _err(f"VERIFY FAILED ({len(failures)} failure(s)):")
        for f in failures[:50]:
            _err(f"  - {f}")
        return EXIT_GATE
    print(f"verify: PASSED — {len(manifest)} manifest entries and "
          f"{n_chunks} chunks fully re-derived")
    return EXIT_OK


def cmd_run(args) -> int:
    """Orchestrate the full gated sequence in order; stop at first failure."""
    if not args.work:
        # Default the staging area beside the published output (mirrors the
        # corpus command's <output>-derived convention). It must never live
        # INSIDE the output: verify() sweeps output recursively and would
        # flag staging files as unmanifested.
        out = Path(args.output)
        args.work = str(out.parent / (out.name + "-work"))
        print(f"run: staging (work) folder defaulted to {args.work}")
    ns = argparse.Namespace
    steps = [
        ("selftest", cmd_selftest, ns(work=args.work)),
        ("scan", cmd_scan, ns(input=args.input, work=args.work,
                              jobs=args.jobs, max_file_bytes=args.max_file_bytes)),
        ("ocr", cmd_ocr, ns(work=args.work, no_ocr=args.no_ocr,
                            endpoint=args.endpoint,
                            allow_loopback_ocr=args.allow_loopback_ocr,
                            google_docai=args.google_docai,
                            project=args.project, processor=args.processor,
                            location=args.location, token_file=args.token_file,
                            allow_cloud_ocr=args.allow_cloud_ocr,
                            export_dir=None, import_dir=None)),
        ("extract", cmd_extract, ns(work=args.work)),
        ("chunk", cmd_chunk, ns(work=args.work, target=args.target,
                                overlap=args.overlap)),
        ("validate", cmd_validate, ns(input=args.input, work=args.work)),
        ("merge", cmd_merge, ns(work=args.work, output=args.output)),
        ("verify", cmd_verify, ns(output=args.output)),
    ]
    for name, fn, step_args in steps:
        print(f"== run: {name} ==")
        rc = fn(step_args)
        if rc != EXIT_OK:
            _err(f"run aborted at stage {name!r} (exit {rc})")
            return rc
    print("run: full gated sequence completed")
    return EXIT_OK


def cmd_corpus(args) -> int:
    """Build (or check) the derived analytical corpus: Parquet + DuckDB +
    seal.json. Derivatives are rebuildable, never evidentiary."""
    from evidence_ingest.corpus import check_corpus, run_corpus
    output = Path(args.output)
    derived = Path(args.derived) if args.derived else output.parent / (output.name + "-derived")
    if args.check:
        failures = check_corpus(output, derived)
        if failures:
            _err(f"CORPUS CHECK FAILED ({len(failures)} failure(s)):")
            for f in failures[:50]:
                _err(f"  - {f}")
            return EXIT_GATE
        print("corpus: check PASSED — all logical roots re-derived and parquet parity holds")
        return EXIT_OK
    stats = run_corpus(output, derived)
    print(f"corpus: {stats['chunks']} chunk(s), {stats['documents']} document(s) "
          f"-> {derived} (duckdb: {stats['duckdb']})")
    print(f"corpus: seal chunks_root={stats['seal']['chunks_root'][:16]}... "
          f"manifest_root={stats['seal']['manifest_root'][:16]}...")
    return EXIT_OK


def cmd_improve(args) -> int:
    """Harvest sanitized issue records for the self-improvement loop.
    Collection is deterministic; analysis/proposals happen in the LLM
    control plane; Ring-0 patches require human approval."""
    from evidence_ingest.improve import run_improve
    n = run_improve(Path(args.work))
    print(f"improve: {n} new issue record(s) appended to _improve/issues.jsonl")
    return EXIT_OK


def cmd_enrich(args) -> int:
    print("advisory enrichment not configured (LLM-free run is complete and authoritative)")
    return EXIT_OK


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evidence-ingest",
        description="Closed-corpus legal-evidence ingestion pipeline "
                    "(deterministic, fail-closed, LLM-free evidentiary path).")
    p.add_argument("--version", action="version", version=TOOL_VERSION)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("selftest", help="red-team gate: 5 adversarial agents "
                        "through the real pipeline; writes _SELFTEST.ok on a "
                        "perfect score. Cannot be skipped.")
    sp.add_argument("--work", required=True)
    sp.set_defaults(fn=cmd_selftest)

    sp = sub.add_parser("scan", help="intake input tree (folder or single file) "
                        "into the content-addressed vault")
    sp.add_argument("--input", required=True,
                    help="source evidence folder or single file (read-only)")
    sp.add_argument("--work", required=True)
    sp.add_argument("--jobs", type=int, default=1)
    sp.add_argument("--max-file-bytes", type=int, default=RunConfig().max_file_bytes)
    sp.set_defaults(fn=cmd_scan)

    sp = sub.add_parser("ocr", help="OCR lane: local Azure Read container "
                        "(loopback), Google Document AI (audited cloud "
                        "exception), --no-ocr, or folder-enclave export/import")
    sp.add_argument("--work", required=True)
    sp.add_argument("--endpoint", help="http://127.0.0.1:PORT of local Read container")
    sp.add_argument("--allow-loopback-ocr", action="store_true",
                    help="explicit consent to open ONE loopback connection")
    sp.add_argument("--no-ocr", action="store_true",
                    help="record ocr_unavailable; never fails the run")
    sp.add_argument("--google-docai", action="store_true",
                    help="use Google Document AI (cloud) — requires "
                         "--allow-cloud-ocr, --project, --processor, --token-file")
    sp.add_argument("--project", help="GCP project id owning the processor")
    sp.add_argument("--processor", help="Document AI processor id (16-char lowercase hex id)")
    sp.add_argument("--location", default="us",
                    help="Document AI region (host {location}-documentai.googleapis.com)")
    sp.add_argument("--token-file",
                    help="file holding a bearer token (gcloud auth print-access-token > file); "
                         "never logged — only its sha256 is custody-recorded")
    sp.add_argument("--allow-cloud-ocr", action="store_true",
                    help="explicit operator acknowledgement of the audited "
                         "cloud-OCR exception (evidence bytes transit TLS to Google)")
    sp.add_argument("--export", dest="export_dir",
                    help="write signed request bundle for an air-gapped OCR host")
    sp.add_argument("--import", dest="import_dir",
                    help="verify and ingest enclave OCR responses")
    sp.set_defaults(fn=cmd_ocr)

    sp = sub.add_parser("extract", help="deterministic parsers -> extraction bundles")
    sp.add_argument("--work", required=True)
    sp.set_defaults(fn=cmd_extract)

    sp = sub.add_parser("chunk", help="deterministic chunker -> rag/chunks.jsonl")
    sp.add_argument("--work", required=True)
    sp.add_argument("--target", type=int, default=None)
    sp.add_argument("--overlap", type=int, default=None)
    sp.set_defaults(fn=cmd_chunk)

    sp = sub.add_parser("validate", help="re-derive everything from bytes; "
                        "writes _VALIDATED.ok only on full pass")
    sp.add_argument("--input", required=True,
                    help="the same folder or single file passed to scan")
    sp.add_argument("--work", required=True)
    sp.set_defaults(fn=cmd_validate)

    sp = sub.add_parser("merge", help="publish work corpus into the locked "
                        "output (requires fresh _SELFTEST.ok + _VALIDATED.ok)")
    sp.add_argument("--work", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(fn=cmd_merge)

    sp = sub.add_parser("verify", help="full re-derivation of all hashes in "
                        "an output corpus")
    sp.add_argument("--output", required=True)
    sp.set_defaults(fn=cmd_verify)

    sp = sub.add_parser("run", help="orchestrate the full gated sequence")
    sp.add_argument("--input", required=True,
                    help="source evidence folder or single file (read-only, never modified)")
    sp.add_argument("--work", required=False, default=None,
                    help="staging folder (default: <output>-work beside the output)")
    sp.add_argument("--output", required=True,
                    help="published corpus folder — all processed data lands here")
    sp.add_argument("--jobs", type=int, default=1)
    sp.add_argument("--max-file-bytes", type=int, default=RunConfig().max_file_bytes)
    sp.add_argument("--no-ocr", action="store_true")
    sp.add_argument("--endpoint")
    sp.add_argument("--allow-loopback-ocr", action="store_true")
    sp.add_argument("--google-docai", action="store_true")
    sp.add_argument("--project")
    sp.add_argument("--processor")
    sp.add_argument("--location", default="us")
    sp.add_argument("--token-file")
    sp.add_argument("--allow-cloud-ocr", action="store_true")
    sp.add_argument("--target", type=int, default=None)
    sp.add_argument("--overlap", type=int, default=None)
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("corpus", help="build/check derived analytical "
                        "corpus (Parquet + DuckDB + Merkle seal) from a "
                        "published output — rebuildable, never evidentiary")
    sp.add_argument("--output", required=True, help="published corpus folder")
    sp.add_argument("--derived", help="derived artifacts folder "
                    "(default: <output>-derived beside the output)")
    sp.add_argument("--check", action="store_true",
                    help="re-derive all logical roots and compare with seal.json")
    sp.set_defaults(fn=cmd_corpus)

    sp = sub.add_parser("improve", help="harvest sanitized issue records "
                        "(drop reasons, warning classes) into "
                        "_improve/issues.jsonl for the improvement loop")
    sp.add_argument("--work", required=True)
    sp.set_defaults(fn=cmd_improve)

    sp = sub.add_parser(
        "enrich",
        help="OPTIONAL advisory tier stub (LLM-free run is authoritative)",
        description=(
            "Model-tier doctrine: Tier 0 (deterministic code) owns the "
            "evidentiary path — every artifact in the output corpus is "
            "produced and verified without any LLM. An optional advisory "
            "tier MAY later annotate copies of the corpus (summaries, "
            "entity hints) but its output is never authoritative, never "
            "cited as evidence, and never feeds back into the evidentiary "
            "artifacts. This stub documents that doctrine and exits 0."))
    sp.set_defaults(fn=cmd_enrich)
    return p


def main(argv: list[str] | None = None) -> int:
    _require_python()
    if not netguard.is_installed():
        netguard.install()
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except GateError as e:
        _err(f"GATE FAILURE: {e}")
        return EXIT_GATE
    except CustodyError as e:
        _err(f"CUSTODY VIOLATION: {e}")
        return EXIT_CUSTODY
    except netguard.NetworkBlockedError as e:
        _err(f"NETWORK POLICY VIOLATION: {e}")
        return EXIT_NETWORK
    except FileNotFoundError as e:
        _err(f"environment unfit: {e}")
        return EXIT_ENVIRONMENT
