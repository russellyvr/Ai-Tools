# evidence-ingest

Closed-corpus legal-evidence ingestion pipeline: **folder in → RAG-ready folder out**.
Deterministic, fail-closed, LLM-free evidentiary path. Python 3.11+, stdlib + pydantic v2 only.

```
python -m evidence_ingest run --input <evidence> --work <staging> --output <corpus> --no-ocr
```

## Architecture and gate order

```
selftest ──► scan ──► ocr ──► extract ──► chunk ──► validate ──► merge ──► verify
(red-team    (vault   (loopback (deterministic (deterministic  (re-derive   (publish,  (full hash
 gate,        capture, container  parsers)      chunker)        everything   lock)      re-derivation)
 no skip)     ledgers) or none)                                 from bytes)
```

* **selftest** runs five adversarial agents through the *real* pipeline code against
  synthetic fixtures in `<work>/_selftest`. It demands **100 % trap neutralization AND
  100 % control acceptance** and writes `_SELFTEST.ok` bound to the sha256 of the code
  tree. There is **no skip flag**, by design.
* **scan** walks the input, rejects symlinks/reparse points/devices via `lstat`-first,
  sniffs magic bytes (pdf/png/jpeg/tiff/bmp/eml/txt), detects sources that change during
  capture (fstat before/after + independent re-hash of the copy), and stores verbatim
  bytes in a content-addressed vault (`vault/sha256/<aa>/<sha>`). Duplicate content is
  stored once; **every occurrence is preserved** in the ledger. Every rejected input gets
  a reason-coded drop record — nothing silently disappears.
* **ocr** routes PDFs/images through the OCR lane (see below) or records
  `ocr_unavailable` with `--no-ocr` (never fails the run).
* **extract** runs deterministic stdlib parsers (`.eml` via `email.parser` with verbatim
  header capture, `.txt`/`.md` as UTF-8 with recorded replacement warnings; PDFs/images
  come only from the stored OCR artifact). Every bundle records `parse_warnings`.
* **chunk** is a deterministic sliding-window chunker (target/overlap chars,
  whitespace-boundary preference). `chunk_id` is content-derived, so every chunk is
  independently re-derivable.
* **validate** re-derives everything from bytes: source↔vault identity, occurrence
  reconciliation (*inputs == accepted + dropped, exactly*), custody chain, path
  confinement, schema re-validation (`extra="forbid"`), chunk offset recomputation.
  Writes `_VALIDATED.ok` only on a full pass.
* **merge** refuses without fresh `_SELFTEST.ok` + `_VALIDATED.ok` matching the current
  code tree and config, then unlock → append-only publish → regen manifests → **re-lock
  in `finally`**.
* **verify** re-derives every hash in a published corpus from scratch.

Exit codes: `0` ok · `2` gate failure · `3` custody violation · `4` network-policy
violation · `5` environment unfit.

## Cloud OCR exception (Google Document AI) — ACTIVE OCR PLAN

**This is a documented, audited exception to the closed-corpus rule**, replacing the
Azure container as the active OCR plan (the Azure/loopback path below remains available
as the air-gapped alternative). The default posture stays fully closed: the exception
exists only while the `ocr` stage runs with **both** `--google-docai` and
`--allow-cloud-ocr`.

**Custody boundary change:** with this exception enabled, the verbatim evidence bytes of
PDF/image records transit TLS to Google's `{location}-documentai.googleapis.com`
endpoint and are processed under your organization's Document AI terms. The
boundary change itself is evidence: adapter construction writes a
`cloud_ocr_exception_enabled` custody event recording the host, the pinned IPs, the full
processor path, the sha256 of the token file, and `operator_ack: true`; every subsequent
connection is custody-logged.

**Audited-allowlist mechanism:** `netguard.allow_cloud_host(hostname, port)` resolves the
hostname exactly **once** through the original resolver, pins all resolved IPs + port
into the allowlist, and admits that literal hostname (and nothing else) through the
guarded `getaddrinfo`. Later connections go only to the pinned IPs — the name is never
re-resolved, so mid-run DNS repinning cannot redirect evidence bytes. Everything else
remains default-deny, and the selftest now includes posture traps proving the Document
AI host is unresolvable and unconnectable unless the exception is active.

**Flags** (all required together, except `--location` which defaults to `us`):

```
python -m evidence_ingest ocr --work W --google-docai --allow-cloud-ocr ^
    --project your-gcp-project-id --processor <PROCESSOR_ID> --location us ^
    --token-file $env:TEMP\docai.token
```

**Example environment (PLACEHOLDER values — substitute your own):** GCP project
`your-gcp-project-id` (the numeric project number, e.g. `000000000000`, works equally
in the URL); an `OCR_PROCESSOR`-type processor in state `ENABLED`, location `us`.
Endpoint shape:
`https://us-documentai.googleapis.com/v1/projects/000000000000/locations/us/processors/<PROCESSOR_ID>:process`.
A pretrained OCR processor version (e.g. `pretrained-ocr-v2.1-2024-08-07`) is resolved
at enable-time. Note:
`:process` responses do **not** echo the processor version — Document AI resolves the
default version at enable-time — so custody records the configured processor path plus
a `processor_version` note, and the enable-time default is documented here.

**Token workflow:** generate a short-lived bearer token yourself (PowerShell, gcloud
installed under `%LOCALAPPDATA%\Google\Cloud SDK`):

```powershell
& "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" auth print-access-token |
    Set-Content -NoNewline $env:TEMP\docai.token
```

then pass `--token-file $env:TEMP\docai.token`. The
tool reads and strips it, sends it only as the `Authorization` header to the pinned
host, and **never logs or stores the token**; only the token file's sha256 is custody-
recorded for provenance. The tool makes no subprocess calls.

**Request/limits:** synchronous `:process` with
`{"rawDocument": {content, mimeType}, "skipHumanReview": true}` (mime map:
pdf/png/jpeg/tiff/bmp). Files over the 20 MiB sync cap (or 15 pages) get the recorded,
reconciled status `too_large_for_sync` — never a crash. HTTP 200 responses are stored
verbatim + hashed in `ocr-raw/<sha>.json` (channel `google-docai-v1` in bundles and
chunks); non-200 responses record status `failed` with the first 500 bytes captured in
custody details.

**Google-side data retention (no server droppings):** the tool uses **only** the
synchronous `:process` API with inline `rawDocument` bytes — it never uploads evidence
to a GCS bucket. Per Google's Document AI security documentation
(<https://docs.cloud.google.com/document-ai/docs/security>), synchronous request data is
"processed in memory, encrypted in flight, and **not persisted to disk**" — there is no
stored copy on Google's side to delete. `skipHumanReview: true` guarantees no copy is
routed to Google's human-review queue, and Google contractually does not use customer
content for model training (Google Cloud Terms of Service §17; Document AI is
FedRAMP High and HIPAA compliant). Only request metadata (timestamp, request size — not
content) is logged by Google. By contrast, Document AI **batch** processing requires GCS
staging with an up-to-one-day TTL on Google's side — the tool's 20 MiB sync-only cap
(`too_large_for_sync`) exists precisely so the pipeline can never silently fall back to
a mode that leaves evidence copies on Google storage.

## The OCR / network tension — air-gapped alternative (Azure container)

A closed corpus must not touch the network; scanned PDFs need OCR. If the cloud
exception above is not acceptable for a matter, use **Azure AI Vision Read 3.2 (GA) as a
locally hosted container**, reached only over loopback:

* The tool's network guard is installed at interpreter start with an **empty allowlist**.
  `ocr --allow-loopback-ocr --endpoint http://127.0.0.1:5000` adds exactly one
  `(loopback-ip, port)` pair. Hostnames never resolve (literal loopback IPs only), the
  container's `Operation-Location` poll URL is re-validated against the same loopback
  origin (escape guard), and every allowed connection is written to the custody log.
* The container's raw JSON is stored **verbatim and hashed** (`ocr-raw/<sha>.json`);
  extraction only ever parses that stored artifact.
* Container install/run: <https://learn.microsoft.com/azure/ai-services/computer-vision/computer-vision-how-to-install-containers>.
  For a **fully offline** (air-gapped) deployment you need Microsoft approval and a
  commitment-tier disconnected-container license:
  <https://learn.microsoft.com/azure/ai-services/containers/disconnected-containers>.
* The Read container requires **x64 with AVX2**. On Apple Silicon (e.g. M4) it will not
  run natively; use **folder-enclave mode** (`ocr --export <dir>` on the analyst machine,
  run the container on a separate x64 host against the exported request bundle, then
  `ocr --import <dir>`; the request manifest is verified before any response is ingested)
  or point `--endpoint` at a loopback tunnel you explicitly own — the tool itself will
  never allowlist a non-loopback address.

## The five red-team agents

| Agent | Attack surface | Traps planted | Oracle (must hold) |
|---|---|---|---|
| **inkwell** | content poisoning | prompt-injection payloads, invisible Unicode (zero-width, bidi), canary strings | bytes preserved verbatim; canaries never influence routing or acceptance |
| **bitrot** | integrity | post-hash bit flips, truncated PDF, appended trailers, magic/extension mismatch | structural traps drop with `TAMPER_*`; post-hash flip caught by validate |
| **masquerade** | metadata spoofing | display-name spoofs, lookalike domains, conflicting/future/pre-epoch dates | headers stay source-tagged untrusted, carried verbatim, never synthesized |
| **doppelganger** | identity/path abuse | exact dupes, case collisions, NFC/NFD twins, reserved names (CON, NUL.txt), traversal names, deep paths | dedup by content sha only; no overwrite; path confinement holds |
| **contortionist** | schema/resource abuse | extra JSON fields, wrong types, CSV-injection cells, control chars/JSONL smuggling, invalid UTF-8, oversized files | `extra="forbid"` rejects; caps drop with `RESOURCE_*`; ledger reconciles |

If a trap ever leaks, **fix the pipeline, not the trap** — the gate is withheld until
the score is perfect.

## Model-tier doctrine

* **Tier 0 — deterministic code owns evidence.** Every artifact in the output corpus is
  produced and verified by deterministic parsers and hashes. **No LLM anywhere in the
  evidentiary path.**
* **Advisory tier (optional, off by default).** `python -m evidence_ingest enrich` is a
  stub that documents the doctrine: an LLM may later *annotate* copies of the corpus,
  but its output is never authoritative, never cited as evidence, and never feeds back
  into evidentiary artifacts. The LLM-free run is complete and authoritative.

## Chain-of-custody design

`_custody.jsonl` is an append-only, hash-chained event log:
`event_hash = sha256(canonical_json(record − event_hash))`, each record carrying the
previous record's hash (`prev_sha256`, genesis = 64 zeros). Any insertion, deletion, or
edit breaks the chain, which is re-verified during `validate` and `verify`. Merge
preserves each run's full chain under `custody-runs/<run_id>.jsonl` (hash recorded in the
corpus chain) and extends the corpus-level chain with the merge event.

## Legal-defensibility rationale

* **Fail-closed:** each stage refuses to run without the previous stage's gate; gates are
  invalidated by any code or config change (bound to `code_tree_sha256`).
* **Byte authority:** the verbatim originals under `evidence/sha256/` are the evidence;
  every derived artifact (bundle, chunk, index) is re-derivable and re-derived from them.
* **Reproducibility:** canonical JSON, sorted keys, LF endings, content-derived IDs —
  identical inputs and code produce byte-identical outputs.
* **Dropped-record accounting:** validation proves *inputs = accepted + dropped* exactly;
  each drop carries a reason code and a custody event. Nothing vanishes silently.

## Output folder layout (RAG-ready)

```
O/
  evidence/sha256/<aa>/<sha>     verbatim original bytes, immutable-flagged
  extracted/<sha>.bundle.json    deterministic extraction bundles
  ocr-raw/<sha>.json             verbatim OCR responses (when OCR ran)
  rag/chunks.jsonl               canonical-JSON chunk records (see below)
  custody-runs/<run_id>.jsonl    full per-run custody chains
  _index.csv                     per-object index (CSV-injection-guarded)
  _MANIFEST.sha256               sha256<TAB>relpath, sorted, LF
  _custody.jsonl                 corpus-level custody chain
  _extraction-report.md          human summary   ·   _audit.json  machine audit
```

Each chunk record carries `schema_version, chunk_id, source_sha256, source_relpaths,
media_type, channel (native-text|azure-read-3.2|none), page_number, char_start/end,
utf8_byte_start/end, text, text_sha256, extraction_sha256, chunk_config_sha256,
tool_version, code_tree_sha256, run_id` and an `embedding` placeholder
(`state:"not_generated"`, null model/dim/vector) — embeddings are generated downstream,
never here.

## Windows → macOS (Apple Silicon) porting notes

* **Immutability:** macOS uses `chflags UF_IMMUTABLE` (uchg); Windows uses the
  `FILE_ATTRIBUTE_READONLY` attribute via ctypes; plain `chmod` is the fallback.
  `locking.py` feature-detects at runtime — no code changes needed.
* **Reserved names / long paths:** Windows access uses `\\?\` extended-length paths so
  reserved device names (CON, NUL.txt) are captured as files, never opened as devices.
  This is a no-op elsewhere.
* **Multiprocessing:** `get_context("spawn")` everywhere (the macOS/Windows default),
  behind `__main__` guards; workers are top-level functions.
* **Paths:** all path handling is `pathlib`; ledgers store POSIX-style relpaths, so
  corpora validate identically across platforms. No shell calls anywhere.
* **OCR:** the Read container is x64/AVX2-only — on Apple Silicon use folder-enclave
  mode (above) or a separate x64 host.

## Install / run

```
pip install pydantic          # the only dependency
python -m evidence_ingest --help
python -m evidence_ingest selftest --work C:\staging
python -m evidence_ingest run --input D:\evidence --work C:\staging --output E:\corpus --no-ocr
```

A tiny demo lives in `demo/` (`demo\run-demo.ps1` or `demo/run-demo.sh`).
