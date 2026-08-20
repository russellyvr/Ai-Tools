# Security posture — evidence-ingest

## What this package does about security

- **No network by default.** A default-deny socket guard is installed before
  any other import. The only egress the pipeline can ever perform is the
  explicitly double-flagged OCR lane (`--google-docai --allow-cloud-ocr`, or
  `--allow-loopback-ocr` to a literal loopback address), pinned to a single
  resolved host. Everything else exits with a network-policy error.
- **No secrets in this repository.** All Google Cloud project, processor, and
  service-account values in code and docs are placeholders. Credentials are
  minted at runtime by `gcloud`, written to a 0600 temp file, passed via
  `--token-file`, deleted on every exit path, and never logged — only the
  token file's sha256 enters the custody record.
- **Untrusted input is the threat model.** Inputs are parsed read-only with
  stdlib/pure-Python parsers: scripts in HTML are never executed, spreadsheet
  formulas stay inert source text, macros never run, links are never fetched.
  A five-agent adversarial selftest (40 traps / 18 controls — corruption,
  formula injection, identity collision, content poisoning, provenance
  spoofing) must pass before any run proceeds.
- **Fail-closed by construction.** Gates are bound to a hash of the package
  source; editing any code stales every gate and forces re-attestation.
  Validation failures stop the pipeline; there is no skip flag.
- **Installers are inert.** They copy documented text files as the current
  user — no sudo, no network, no configuration changes.

## Operator responsibilities

- Supply your own Google Cloud project/processor and confirm your
  organization's Document AI data-governance terms before enabling the cloud
  OCR exception; the enablement is custody-recorded on purpose.
- Treat the published corpus as the sole evidentiary authority; derived
  Parquet/DuckDB artifacts are rebuildable caches.
- Run `verify` after every merge and before relying on a corpus.

## Reporting a vulnerability

Open a GitHub issue on this repository. For anything sensitive, use GitHub's
private vulnerability reporting ("Report a vulnerability" under the Security
tab) so details stay out of the public tracker until fixed.
