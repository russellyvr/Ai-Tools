---
name: evidence-ingest
description: Closed-corpus ingestion pipeline (folder in, folder out) for legal evidence AND general documents. Use when the user wants to ingest, stage, validate, publish, or analyze files (.eml, .txt, .md, .csv, .html, .htm, .doc, .docx, .xls, .xlsx, PDFs, images) into a locked, RAG-ready corpus with chain of custody, plus derived Parquet/DuckDB analytics. OCR runs via Google Document AI (audited cloud exception, --google-docai --allow-cloud-ocr) or a local loopback Azure Read container / folder-enclave as the air-gapped alternative. Deterministic and LLM-free on the evidentiary path; LLM swarms orchestrate and audit only.
---

# ingest skill (v2 — corpus mode, macOS)

Tool location: `tool/` inside this skill folder, so the skill is fully
self-contained. It works as an agent skill for Claude Code
(`~/.claude/skills/evidence-ingest/`) or GitHub Copilot CLI
(`~/.copilot/skills/evidence-ingest/`). Run the launcher `tool/ingest.sh` from
anywhere; it resolves the bundled virtualenv (`tool/.venv`) automatically — no
activation, no `PYTHONPATH`. Requires Python 3.11+, `pydantic` v2; corpus mode
additionally uses `pyarrow`, `duckdb`, `openpyxl`, `python-docx`, `pandas`;
oversized-PDF OCR splitting uses `pypdf`. Provision the virtualenv once:
`cd tool && python3 -m venv .venv && .venv/bin/pip install "pydantic>=2.5,<3"`
(add the corpus-mode extras if you use `corpus`).

Launcher: `ingest.sh` (macOS Apple Silicon / Intel) — a thin wrapper over
`python3 -m evidence_ingest`. The Python core is byte-identical to the Windows
deployment (`ingest.ps1`).

> **Note — OCR plans:** the ACTIVE plan is Google Document AI (cloud, audited
> exception; supply your own project/processor/location and a short-lived access
> token file). The Azure Read container remains the air-gapped alternative.
> `--no-ocr` is always safe (text/tabular/OOXML ingestion is complete and
> authoritative).

## Two-plane doctrine (non-negotiable)

- **Ring 0 — data plane (deterministic, LLM-FREE):** every byte that becomes
  corpus (scan → OCR → extract → chunk → validate → merge → verify → corpus)
  is produced by code, never by a model. No LLM output may be written into
  the work, output, or derived folders.
- **Rings 1–3 — control plane (LLM swarms allowed):** orchestration, triage,
  result summarization, issue clustering, and improvement proposals. Route
  cheap/mechanical dispatches (stage runners, pass-fail reporting, input-folder
  triage, format census, validation-report summarization) to an ECONOMY model at
  low effort. ANY change to validators, red team, netguard, custody, or hashing
  goes to a FRONTIER model at maximum effort (FLOOR — never drifts down).
  Name the routed tier + effort in the progress update when delegating.

## Supported formats

| Formats | Lane |
|---|---|
| `.txt` `.md` `.csv` | native text, verbatim (CSV shape recorded, formulas inert) |
| `.html` `.htm` | deterministic stdlib `html.parser` visible-text extraction; scripts never executed, links/resources never fetched; script/style/template blocks and comments excluded from text with counted parse warnings (vault bytes stay authoritative); `<title>` captured as subject |
| `.docx` `.xlsx` | deterministic pure-Python parsers (python-docx / openpyxl read-only); formulas stay source text, macros/links never executed |
| `.doc` `.xls` | preserved verbatim in vault, marked `needs_conversion` — convert offline via `soffice --headless --convert-to docx/xlsx` (macros disabled, network denied) and re-ingest |
| `.eml` | RFC5322 verbatim headers + recipients |
| `.pdf` `.png` `.jpg` `.jpeg` `.tif` `.bmp` | OCR lane (Google Doc AI sync `:process`, inline bytes, skipHumanReview; batch mode forbidden). PDFs over the 20 MiB sync cap are deterministically split in-memory (pypdf, 15-page slices) and OCR'd per slice via the same sync path; the stored artifact assembles every part's verbatim response with original page numbering. Fail-closed fallback: `too_large_for_sync`. |

## Invocation

```bash
"<skill folder>/tool/ingest.sh" <command> ...     # launcher (uses the bundled venv)
# equivalently:
cd "<skill folder>/tool" && .venv/bin/python3 -m evidence_ingest <command> ...
```

## Run order (gated; each stage refuses without the prior gate)

1. `selftest --work W` — red-team gate (5 adversarial agents, 40 traps / 18
   controls incl. OOXML/CSV/HTML attacks); writes `_SELFTEST.ok`. Run first, always.
2. `scan --input I --work W [--jobs N]` — capture to content-addressed vault
   (`--input` may be a folder, walked recursively, or a single file).
3. OCR — pick exactly one lane:
   - ACTIVE PLAN (audited cloud exception, Google Document AI):
     `ocr --work W --google-docai --allow-cloud-ocr --project <PROJECT> --processor <PROCESSOR_ID> --location us --token-file <file>`
     Token file (never logged; sha256 custody-recorded):
     `gcloud auth print-access-token > "$TMPDIR/docai.token"`
   - No OCR: `ocr --work W --no-ocr`
   - Air-gapped alternative: `ocr --work W --endpoint http://127.0.0.1:5000 --allow-loopback-ocr`
   - Enclave: `ocr --work W --export DIR` then later `ocr --work W --import DIR`.
4. `extract --work W`
5. `chunk --work W [--target 2000] [--overlap 200]`
6. `validate --input I --work W` — writes `_VALIDATED.ok` only on full pass.
7. `merge --work W --output O` — publishes and locks the corpus.
8. `verify --output O` — full hash re-derivation; run after every merge.
9. `corpus --output O [--derived D]` — build derived Parquet + DuckDB +
   Merkle `seal.json` (rebuildable, NEVER evidentiary).
   `corpus --output O --derived D --check` — re-derive all logical roots.

Or one shot: `run --input I --output O --no-ocr` (staging defaults to
`<output>-work` beside the output; override with `--work W`) then `corpus`.
Launcher-only extra: `run ... --clean` (ingest.sh, Ring 1 — never forwarded to
Python). After a successful run the launcher re-runs `verify --output O` and,
only on pass, deletes the work folder contents except `_improve/`
(self-improvement issue log kept). On verify failure the work folder is retained
and the exit code propagates. Requires `--output`. The input may be a folder or a
single file; the output is always a folder distinct from the input. The input is
read-only and never modified.

Exit codes: 0 ok · 2 gate failure · 3 custody violation · 4 network policy · 5 environment unfit.

## Five validation levels (all deterministic code)

- **L1 Admission** — magic/extension agreement, structural (PDF EOF, PNG
  IEND, ZIP EOCD) checks, dedup, fail-closed accounting (scan).
- **L2 Byte integrity** — custody hash chain + vault/source re-hash (validate).
- **L3 Structural** — pydantic `extra="forbid"` re-validation, path
  confinement, ledger reconciliation (validate).
- **L4 Semantic reconciliation** — re-parse equivalence, chunk offset/hash/id
  re-derivation (validate), Parquet↔JSONL id parity (corpus --check).
- **L5 Seal & release** — manifest re-derivation (verify), Merkle roots
  (chunks/documents/manifest) vs `seal.json` (corpus --check).

An OPTIONAL advisory L5b (ECONOMY swarm sampling chunks vs. source,
non-gating) may FLAG a corpus for human review, never pass a failing one.

## Five-agent red team (selftest gate)

bitrot (integrity corruption incl. Parquet/ZIP truncation) · contortionist
(schema/resource abuse, xlsx/csv formula injection) · doppelganger (identity
collision, unicode twins, reserved names) · inkwell (prompt-injection /
content poisoning canaries) · masquerade (provenance spoofing). Runs against
synthetic fixtures in `<work>/_selftest` through the REAL pipeline code —
never the live corpus. Gates are code-tree-hash bound: any code edit stales
every gate and forces re-attestation.

## Self-improvement loop (self-proposing, never self-authorizing)

1. After every run, append anomalies/gate failures/unexpected drops to
   `<work>/_improve/issues.jsonl` (sanitized — no evidence text, ever).
2. On request (`/ingest improve`): an ECONOMY swarm clusters issues (low
   effort); a FRONTIER agent (max effort — output feeds a gate) writes ranked
   proposals to `_improve/proposals/NNN/` (problem, diff, risk ring, test
   plan, failing-first regression test).
3. Application policy:
   - **Ring 1/2** (this SKILL.md, launchers, orchestration): may auto-apply;
     git-commit each change.
   - **Ring 0** (evidence_ingest package): HUMAN APPROVAL REQUIRED. After
     apply, code-tree hash changes → all gates stale → selftest must re-pass.
   - **Ratchet rule:** proposals may ADD checks/traps; never delete or
     weaken one without an explicit, recorded waiver from the user.
4. Better agent models automatically improve Rings 1–3; Ring 0 has zero model
   dependency and can never degrade as models change.

## Hard rules for the agent

- **Never skip the selftest.** There is no skip flag; do not attempt to work
  around the gate by touching gate files — a stale gate is refused by
  code-tree hash binding.
- **Cloud OCR ONLY via `--google-docai --allow-cloud-ocr`**, and only to host
  `{location}-documentai.googleapis.com` (default `us-documentai.googleapis.com`).
  Documented, audited exception recorded in the custody chain
  (`cloud_ocr_exception_enabled`). Never any other cloud endpoint, never
  without the explicit allow flag (the netguard exits 4; do not try to
  defeat it). Sync-only `:process` with inline bytes — never batch mode (it
  stages evidence in GCS). Source: <https://docs.cloud.google.com/document-ai/docs/security>.
- **Never log, echo, or store the bearer token**; pass it only via `--token-file`.
- **Local `--endpoint` must be a literal loopback IP** (`127.0.0.1`/`::1`).
- If `validate`, `verify`, or `corpus --check` fails, treat the corpus as
  suspect: report the failure list, do not hand-edit ledgers, custody logs,
  vault objects, or seals.
- `--no-ocr` is safe and never fails the run; PDFs/images are preserved
  verbatim and marked `ocr_unavailable` for a later OCR pass.
- `.doc`/`.xls` are preserved verbatim and marked `needs_conversion`; run
  LibreOffice conversion offline (network denied at OS level) and re-ingest
  the converted OOXML files.
- No LLM output may be written into the work, output, or derived folders;
  `enrich` is an advisory stub only.
- DuckDB/LanceDB/Parquet derivatives are rebuildable caches — the published
  output folder is the sole evidentiary authority; embeddings, if added
  later, use a locally pre-installed model only (no runtime egress).
