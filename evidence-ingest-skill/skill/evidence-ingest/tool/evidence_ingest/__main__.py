"""Entry point: ``python -m evidence_ingest <cmd>``.

SECURITY: the network guard is installed at import time, before any other
package module (or third-party import) gets a chance to open a socket. Do
not reorder these imports.
"""
from __future__ import annotations

from evidence_ingest import netguard

netguard.install()

from evidence_ingest.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
