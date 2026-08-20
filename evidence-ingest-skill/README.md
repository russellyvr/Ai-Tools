# evidence-ingest — deterministic closed-corpus ingestion with chain of custody

I built this skill to analyze evidence for CMMC v.2 Level 1 and ISO 27001:2022
compliance, initially based on Microsoft's compliance assessments within 
Purview which I discovered are not themselves following the specifications 
as they offer 'Microsoft suggests' criteria which skew results against the 
published standards.

I used the skill to ingest the published standard, the Microsoft Purview 
Report and Evidence, along with supporting evidence.  Then using the Ai Council 
skill had that evaluated and a gap analysis created - along with an HTML
dashboard to track progress.

A folder-in, folder-out document ingestion pipeline that turns a directory of
mixed files into a locked, RAG-ready (Retrieval-Augmented Generation) corpus —
with a legal-grade provenance record attached to every byte. It ingests
documents of any kind: business records, email archives, research collections,
scanned paper. It was built to legal-evidence standards, and those standards
travel with it even when the content is mundane.

Ships as an agent skill for **Claude Code** and **GitHub Copilot CLI**, plus a
standalone Python CLI (`python -m evidence_ingest`) that needs no agent at all.

Full documentation: [`docs/index.html`](docs/index.html) · deep operator manual:
[`skill/evidence-ingest/tool/README.md`](skill/evidence-ingest/tool/README.md) ·
skill definition: [`skill/evidence-ingest/SKILL.md`](skill/evidence-ingest/SKILL.md)

## Why deterministic and LLM-free

Every byte that becomes corpus — scan → OCR → extract → chunk → validate →
merge → verify — is produced by code, never by a model. Language models may
orchestrate runs, summarize reports, and propose improvements, but no model
output is ever written into the evidentiary path. Two reasons:

- **Reproducibility is the proof.** Every artifact can be re-derived from the
  source bytes and checked hash-for-hash. A model in the data path would make
  the corpus unverifiable and its provenance claims unfalsifiable.
- **Zero hallucination surface.** Extraction is stdlib and pure-Python parsing
  with recorded parse warnings — there is nothing in the pipeline that can
  invent content, so downstream retrieval inherits a clean floor.

## Supported input types

| Formats | Lane |
|---|---|
| `.txt` `.md` `.csv` | native text, verbatim (CSV shape recorded, formulas inert) |
| `.html` `.htm` | stdlib visible-text extraction; scripts never executed, resources never fetched |
| `.docx` `.xlsx` | pure-Python read-only parsers; formulas stay source text, macros never run |
| `.doc` `.xls` | preserved verbatim, marked `needs_conversion` for offline conversion |
| `.eml` | RFC 5322 verbatim headers + typed recipients |
| `.pdf` `.png` `.jpg` `.jpeg` `.tif` `.bmp` | OCR lane (cloud or local — see below), or preserved verbatim with `--no-ocr` |

## Legal provenance (chain of custody)

- **Hash-chained custody log** (`_custody.jsonl`): every pipeline event is
  appended to a tamper-evident sha256 chain — including OCR network activity
  and the enabling of any policy exception.
- **Content-addressed vault**: source bytes are stored under their own sha256;
  nothing is renamed, rewritten, or normalized.
- **Manifest + Merkle seal**: the published corpus carries a full manifest and
  Merkle roots (`seal.json`); `verify` re-derives everything from bytes.
- **Drop-record accounting**: nothing disappears silently — every rejected or
  skipped input is recorded with a reason, and validation reconciles counts.
- **Immutability**: the published corpus is filesystem-locked after merge.

## Security mechanisms

- **Default-deny network guard** (`netguard.py`): a socket-layer allowlist
  installed before any other import. The pipeline can reach nothing unless a
  specific, flagged exception admits one host — resolved once, IP-pinned, so
  mid-run DNS repinning cannot redirect evidence bytes.
- **Fail-closed gates bound to the code tree**: `selftest` and `validate`
  write gate files keyed to a hash of the package source; any code edit stales
  every gate and forces re-attestation. Later stages refuse to run without
  the prior gate. There is no skip flag.
- **Five-agent deterministic red team** runs inside `selftest` on every run:
  bitrot (corruption), contortionist (schema/formula abuse), doppelganger
  (identity collision, unicode twins), inkwell (content poisoning canaries),
  masquerade (provenance spoofing) — 40 traps and 18 controls through the real
  pipeline code against synthetic fixtures.
- **Byte-level re-derivation**: five validation levels, ending in full
  manifest and Merkle re-derivation from source bytes at `verify`.
- **Ephemeral credentials**: cloud OCR takes a short-lived bearer token via
  `--token-file` (0600, deleted on exit); the token is never logged or stored —
  only its sha256 enters the custody record.
- **Audited cloud exception**: the only permitted cloud egress is the
  explicitly flagged OCR lane below, and enabling it is itself a recorded
  custody event.

## OCR mechanisms

Pick exactly one lane per run:

- **Google Document AI** (cloud — documented, audited exception):
  `ocr --work W --google-docai --allow-cloud-ocr --project your-gcp-project-id
  --processor <PROCESSOR_ID> --location us --token-file <file>`. Both flags are
  required; the guard admits only `{location}-documentai.googleapis.com`;
  sync-only `:process` with inline bytes (batch mode is refused — it would
  stage evidence in cloud storage). `docai-run.sh` wraps the token mint via
  `gcloud` service-account impersonation. All project/processor values in this
  repo are placeholders — supply your own.
- **Local loopback** (air-gapped alternative): a local OCR container on a
  literal loopback address — `ocr --work W --endpoint http://127.0.0.1:5000
  --allow-loopback-ocr` — or fully offline folder-enclave export/import.
- **No OCR**: `--no-ocr` is always safe; PDFs and images are preserved
  verbatim and marked for a later OCR pass.

## Install

```sh
# macOS / Linux — pick your CLI:
./install.sh --claude          # → ~/.claude/skills/evidence-ingest
./install.sh --copilot         # → ~/.copilot/skills/evidence-ingest

# Windows (PowerShell 7+):
pwsh -File .\install.ps1 -Claude    # add -WhatIf to preview
pwsh -File .\install.ps1 -Copilot
```

Installers run as the current user only, make no network calls, download
nothing, and never touch configuration — they copy the skill folder,
backup-first. Then provision the tool's virtualenv once (required — the
red-team gate builds OOXML fixtures):

```sh
cd <installed skill>/tool
python3 -m venv .venv
.venv/bin/pip install "pydantic>=2.5,<3" python-docx openpyxl
# optional, for corpus-mode analytics and oversized-PDF splitting:
.venv/bin/pip install pyarrow duckdb pandas pypdf
```

Prerequisites: Python 3.11+. The standalone CLI works without any agent:
`./skill/evidence-ingest/tool/ingest.sh run --input IN --output OUT --no-ocr`.

## Quick start

```sh
skill/evidence-ingest/tool/demo/run-demo.sh
```

Runs the full gated sequence over a synthetic four-document corpus (no OCR, no
network): red-team selftest, scan into the vault, extract, chunk, validate,
merge, and byte-level verify — then inspect `demo/out/corpus/` to see the
vault, `_custody.jsonl`, manifest, and RAG chunks it produced.

## Layout

```
evidence-ingest-skill/
  install.sh / install.ps1     dual-target installers (Claude Code / Copilot CLI)
  docs/index.html              full documentation page
  SECURITY.md                  security posture and reporting
  skill/evidence-ingest/
    SKILL.md                   agent skill definition (both CLIs)
    tool/                      the pipeline: Python package, launchers, demo
```

License: MIT (repository-level [LICENSE](../LICENSE)).
