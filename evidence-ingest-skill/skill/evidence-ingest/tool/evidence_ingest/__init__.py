"""evidence-ingest — closed-corpus legal-evidence ingestion pipeline.

Folder in -> gated deterministic pipeline -> RAG-ready folder out.

Doctrine:
  * Tier 0 (deterministic code) owns the evidentiary path. NO LLM anywhere
    in it. LLM output is optional advisory tier only, never authoritative.
  * Fail-closed: every stage gate must pass or downstream stages refuse.
  * Byte authority: the verbatim source bytes in the content-addressed
    vault are the evidence; everything else is re-derivable from them.
"""
from __future__ import annotations

__version__ = "1.1.0"
TOOL_VERSION = f"evidence-ingest/{__version__}"

# CLI exit codes (contract; do not renumber).
EXIT_OK = 0
EXIT_GATE = 2          # gate failure (selftest miss, validation failure, stale gate)
EXIT_CUSTODY = 3       # custody chain violation
EXIT_NETWORK = 4       # network-policy violation
EXIT_ENVIRONMENT = 5   # environment unfit (bad python, missing deps, unusable fs)
