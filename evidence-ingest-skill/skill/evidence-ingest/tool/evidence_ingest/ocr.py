"""OCR lane: local Azure Read container (loopback), Google Document AI
(audited cloud exception), or Null.

The evidentiary rules:
  * Default network policy: loopback only. The Google Document AI adapter is
    a DOCUMENTED, AUDITED EXCEPTION — it requires both ``--google-docai``
    and ``--allow-cloud-ocr``, pins the resolved endpoint IPs via
    ``netguard.allow_cloud_host`` and custody-logs the boundary change.
  * The OCR service's raw JSON response is stored verbatim in
    ``work/ocr-raw/<sha>.json`` and hashed; extraction parses only that
    stored artifact, never a live response.
  * NullOcr (``--no-ocr``) records ``ocr_unavailable`` for every OCR-lane
    record and never fails the run.
  * Folder-enclave mode exports a signed request bundle for an air-gapped
    OCR host and imports verified responses.
"""
from __future__ import annotations

import base64
import http.client
import io
import json
import ssl
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from evidence_ingest import TOOL_VERSION, netguard
from evidence_ingest.custody import CustodyLog
from evidence_ingest.hashing import canonical_json, sha256_of, sha256_of_bytes, write_manifest, read_manifest
from evidence_ingest.scan import load_records

OCR_MEDIA_TYPES = {"pdf", "png", "jpeg", "tiff", "bmp"}
READ_ANALYZE_PATH = "/vision/v3.2/read/analyze"
_POLL_INTERVAL_S = 1.0
_POLL_TIMEOUT_S = 300.0


class OcrError(Exception):
    pass


class OcrAdapter(Protocol):
    name: str

    def ocr_file(self, vault_path: Path, sha256: str) -> tuple[str, bytes] | None:
        """Return (status, raw_json_bytes) or None when OCR is unavailable."""
        ...


class NullOcr:
    """Records unavailability; never raises, never blocks the run."""

    name = "null"

    def ocr_file(self, vault_path: Path, sha256: str) -> None:
        return None


def _validate_loopback_url(url: str) -> tuple[str, int, str]:
    """Parse and enforce: plain http, literal loopback host, explicit-ish port.

    Returns (ip, port, base_path). Raises NetworkBlockedError otherwise —
    including for the Operation-Location escape guard.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http":
        raise netguard.NetworkBlockedError(
            f"only http:// to loopback is permitted, got {parsed.scheme!r}")
    host = parsed.hostname or ""
    if host not in ("127.0.0.1", "::1"):
        raise netguard.NetworkBlockedError(
            f"OCR endpoint host must be literal 127.0.0.1 or ::1, got {host!r}")
    port = parsed.port or 80
    return host, port, parsed.path or "/"


class AzureReadContainer:
    """Adapter for the Azure AI Vision Read 3.2 container over loopback.

    Uses http.client directly (no urllib opener chain, no proxies, no
    redirects). Flow: POST bytes -> 202 + Operation-Location -> poll until
    ``status: succeeded`` -> store raw JSON verbatim.
    """

    name = "azure-read-3.2"

    def __init__(self, endpoint: str, custody: CustodyLog):
        self.ip, self.port, base = _validate_loopback_url(endpoint)
        self.base_path = base.rstrip("/")
        self.custody = custody
        netguard.allow_loopback(self.ip, self.port)
        netguard.set_connection_logger(self._log_connection)

    def _log_connection(self, ip: str, port: int) -> None:
        self.custody.append("network_connection_allowed", {
            "ip": ip, "port": port, "purpose": "azure-read-container"})

    def _conn(self) -> http.client.HTTPConnection:
        host = self.ip if ":" not in self.ip else f"[{self.ip}]"
        return http.client.HTTPConnection(host, self.port, timeout=30)

    def ocr_file(self, vault_path: Path, sha256: str) -> tuple[str, bytes]:
        data = vault_path.read_bytes()
        conn = self._conn()
        try:
            conn.request("POST", self.base_path + READ_ANALYZE_PATH, body=data,
                         headers={"Content-Type": "application/octet-stream"})
            resp = conn.getresponse()
            body = resp.read()
            if resp.status != 202:
                raise OcrError(f"analyze returned {resp.status}: {body[:500]!r}")
            op_loc = resp.getheader("Operation-Location")
        finally:
            conn.close()
        if not op_loc:
            raise OcrError("202 without Operation-Location header")
        # Escape guard: the poll URL the container hands back must itself be
        # the same loopback origin; otherwise it is an exfiltration attempt.
        ip, port, poll_path = _validate_loopback_url(op_loc)
        if (ip, port) != (self.ip, self.port):
            raise netguard.NetworkBlockedError(
                f"Operation-Location escaped allowlisted origin: {op_loc!r}")
        query = urllib.parse.urlsplit(op_loc).query
        if query:
            poll_path = poll_path + "?" + query

        deadline = time.monotonic() + _POLL_TIMEOUT_S
        while True:
            conn = self._conn()
            try:
                conn.request("GET", poll_path)
                resp = conn.getresponse()
                raw = resp.read()
                if resp.status != 200:
                    raise OcrError(f"poll returned {resp.status}: {raw[:500]!r}")
            finally:
                conn.close()
            status = json.loads(raw).get("status", "")
            if status == "succeeded":
                return "succeeded", raw
            if status == "failed":
                return "failed", raw
            if time.monotonic() > deadline:
                raise OcrError(f"poll timed out for {sha256}")
            time.sleep(_POLL_INTERVAL_S)


# ---- Google Document AI (audited cloud exception) ----------------------------

_DOCAI_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
}
DOCAI_SYNC_MAX_BYTES = 20 * 1024 * 1024  # 20 MiB sync :process request cap
DOCAI_SYNC_MAX_PAGES = 15                # sync :process page cap


def _pdf_page_count(data: bytes) -> int | None:
    """Deterministically count PDF pages in memory; None when unparseable."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None


def _split_pdf_for_sync(data: bytes) -> list[tuple[int, int, bytes]] | None:
    """Deterministically split an oversized PDF into sync-sized parts.

    Pure in-memory pypdf page copy — the original vault object is never
    modified and the split bytes are transient request payloads, never
    corpus evidence (only the stored OCR responses are). Returns a list of
    (page_start, page_end, part_bytes) with 1-based inclusive page ranges,
    or None when pypdf is unavailable, the PDF cannot be parsed, or any
    single slice still exceeds the sync byte cap.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(data))
        n = len(reader.pages)
        if n == 0:
            return None
        parts: list[tuple[int, int, bytes]] = []
        for start in range(0, n, DOCAI_SYNC_MAX_PAGES):
            end = min(start + DOCAI_SYNC_MAX_PAGES, n)
            writer = PdfWriter()
            for p in range(start, end):
                writer.add_page(reader.pages[p])
            buf = io.BytesIO()
            writer.write(buf)
            part = buf.getvalue()
            if len(part) > DOCAI_SYNC_MAX_BYTES:
                return None  # a single slice is still too big for sync
            parts.append((start + 1, end, part))
        return parts
    except Exception:
        return None


class GoogleDocAIAdapter:
    """Adapter for Google Document AI ``:process`` (Document OCR processor).

    DOCUMENTED, AUDITED EXCEPTION to the closed-corpus rule: evidence bytes
    transit TLS to ``{location}-documentai.googleapis.com``. Construction is
    only reachable from the ``ocr`` CLI stage when the operator passed BOTH
    ``--google-docai`` and ``--allow-cloud-ocr``; it pins the resolved IPs
    via ``netguard.allow_cloud_host`` and writes a
    ``cloud_ocr_exception_enabled`` custody event recording host, pinned
    IPs, processor path, and operator acknowledgement.

    The bearer token is read from ``token_file`` (generated by the operator
    with ``gcloud auth print-access-token > file``); the token itself is
    NEVER logged or stored — only the sha256 of the token file is custody-
    logged for provenance.
    """

    name = "google-docai-v1"

    def __init__(self, project: str, processor_id: str, location: str,
                 token_file: Path, custody: CustodyLog):
        if not project or not processor_id:
            raise OcrError("google-docai requires --project and --processor")
        self.location = (location or "us").strip().lower()
        self.host = f"{self.location}-documentai.googleapis.com"
        self.port = 443
        self.path = (f"/v1/projects/{project}/locations/{self.location}"
                     f"/processors/{processor_id}:process")
        token_file = Path(token_file)
        self._token = token_file.read_text(encoding="utf-8").strip()
        if not self._token:
            raise OcrError(f"token file is empty: {token_file}")
        self.custody = custody
        resolved = netguard.allow_cloud_host(self.host, self.port)
        netguard.set_connection_logger(self._log_connection)
        custody.append("cloud_ocr_exception_enabled", {
            "host": self.host,
            "port": self.port,
            "resolved_ips": resolved,
            "processor_path": self.path,
            "processor_version": ("resolved at enable-time by Document AI "
                                  "(default version; not echoed in :process "
                                  "responses)"),
            "token_file_sha256": sha256_of(token_file),
            "operator_ack": True,
        })

    def _log_connection(self, ip: str, port: int) -> None:
        self.custody.append("network_connection_allowed", {
            "ip": ip, "port": port, "purpose": "google-docai"})

    def ocr_file(self, vault_path: Path, sha256: str) -> tuple[str, bytes] | None:
        data = vault_path.read_bytes()
        media = _sniff_media_for_docai(vault_path, data)
        if media == "pdf" and len(data) <= DOCAI_SYNC_MAX_BYTES:
            # Sync :process also enforces a page cap, not just a byte cap:
            # small-but-long PDFs must take the deterministic split path too.
            n_pages = _pdf_page_count(data)
            if n_pages is not None and n_pages > DOCAI_SYNC_MAX_PAGES:
                parts = _split_pdf_for_sync(data)
                if parts is not None:
                    return self._ocr_pdf_parts(sha256, parts)
        if len(data) > DOCAI_SYNC_MAX_BYTES:
            if media == "pdf":
                parts = _split_pdf_for_sync(data)
                if parts is not None:
                    return self._ocr_pdf_parts(sha256, parts)
            # Recorded, reconciled outcome — the 20 MiB / 15-page sync limit
            # is a service constraint, never a crash. Reached only when the
            # deterministic split path is unavailable or insufficient.
            return "too_large_for_sync", canonical_json({
                "status": "too_large_for_sync",
                "size_bytes": len(data),
                "limit_bytes": DOCAI_SYNC_MAX_BYTES,
            }).encode("utf-8")
        mime = _DOCAI_MIME.get(media)
        if mime is None:
            return "failed", canonical_json({
                "status": "failed", "reason": f"unsupported media {media!r}"}).encode("utf-8")
        return self._process_bytes(data, mime, sha256)

    def _ocr_pdf_parts(self, sha256: str,
                       parts: list[tuple[int, int, bytes]]) -> tuple[str, bytes]:
        """OCR each sync-sized PDF slice and assemble one stored artifact.

        Every part's verbatim :process response is embedded (parsed, then
        canonically re-serialized) together with its 1-based source page
        range, so extraction can renumber pages back to the original
        document. Any part failure fails the whole file — no partial text.
        """
        self.custody.append("ocr_pdf_split_for_sync", {
            "sha256": sha256, "adapter": self.name, "parts": len(parts),
            "max_part_pages": DOCAI_SYNC_MAX_PAGES})
        assembled = []
        for page_start, page_end, part in parts:
            state, raw = self._process_bytes(
                part, "application/pdf", f"{sha256}:p{page_start}-{page_end}")
            if state != "succeeded":
                return "failed", canonical_json({
                    "status": "failed",
                    "reason": "part_ocr_failed",
                    "page_start": page_start, "page_end": page_end,
                    "detail": raw[:500].decode("utf-8", errors="replace"),
                }).encode("utf-8")
            assembled.append({
                "page_start": page_start,
                "page_end": page_end,
                "part_sha256": sha256_of_bytes(part),
                "response": json.loads(raw),
            })
        return "succeeded", canonical_json({
            "assembled_from_parts": True,
            "adapter": self.name,
            "source_sha256": sha256,
            "parts": assembled,
        }).encode("utf-8")

    def _process_bytes(self, data: bytes, mime: str,
                       request_id: str) -> tuple[str, bytes]:
        body = canonical_json({
            "rawDocument": {
                "content": base64.b64encode(data).decode("ascii"),
                "mimeType": mime,
            },
            "skipHumanReview": True,
        }).encode("utf-8")
        conn = http.client.HTTPSConnection(
            self.host, self.port, timeout=120,
            context=ssl.create_default_context())
        try:
            conn.request("POST", self.path, body=body, headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json; charset=utf-8",
            })
            resp = conn.getresponse()
            raw = resp.read()
        finally:
            conn.close()
        if resp.status == 200:
            return "succeeded", raw
        self.custody.append("ocr_request_failed", {
            "sha256": request_id, "adapter": self.name,
            "http_status": resp.status,
            "response_head": raw[:500].decode("utf-8", errors="replace"),
        })
        return "failed", raw


def _sniff_media_for_docai(vault_path: Path, data: bytes) -> str:
    from evidence_ingest.scan import sniff_magic
    return sniff_magic(data[:64])


def run_ocr(work: Path, adapter: OcrAdapter, custody: CustodyLog) -> dict[str, str]:
    """Run the OCR lane over every pdf/image record; write ocr-raw + status."""
    work = Path(work)
    records = load_records(work)
    (work / "ocr-raw").mkdir(exist_ok=True)
    status: dict[str, str] = {}
    for sha in sorted(records):
        rec = records[sha]
        if rec.media_type not in OCR_MEDIA_TYPES:
            status[sha] = "not_applicable"
            continue
        out = adapter.ocr_file(work / rec.vault_relpath, sha)
        if out is None:
            status[sha] = "ocr_unavailable"
            custody.append("ocr_unavailable", {"sha256": sha, "adapter": adapter.name})
            continue
        state, raw = out
        status[sha] = state
        if state != "succeeded":
            custody.append("ocr_not_performed", {
                "sha256": sha, "adapter": adapter.name, "status": state,
                "detail": raw[:500].decode("utf-8", errors="replace")})
            continue
        raw_path = work / "ocr-raw" / f"{sha}.json"
        raw_path.write_bytes(raw)
        raw_sha = sha256_of_bytes(raw)
        custody.append("ocr_response_stored", {
            "sha256": sha, "adapter": adapter.name,
            "ocr_raw_sha256": raw_sha, "status": state})
    _write_status(work, adapter.name, status)
    custody.append("ocr_completed", {"adapter": adapter.name,
                                     "counts": _count(status)})
    return status


def _write_status(work: Path, adapter_name: str, status: dict[str, str]) -> None:
    (work / "ledger" / "ocr-status.json").write_text(
        canonical_json({"adapter": adapter_name, "status": status,
                        "utc": datetime.now(timezone.utc).isoformat()}) + "\n",
        encoding="utf-8")


def _count(status: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in status.values():
        out[v] = out.get(v, 0) + 1
    return out


# ---- folder-enclave mode (air-gapped OCR host) -------------------------------

def ocr_export(work: Path, export_dir: Path, custody: CustodyLog) -> int:
    """Write a signed request bundle for an offline OCR host.

    Copies every OCR-lane vault object plus a manifest binding each request
    to its content sha. The enclave host runs the Read container locally and
    returns ``responses/<sha>.json`` files.
    """
    work, export_dir = Path(work), Path(export_dir)
    records = load_records(work)
    req_dir = export_dir / "requests"
    req_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "responses").mkdir(exist_ok=True)
    n = 0
    for sha in sorted(records):
        rec = records[sha]
        if rec.media_type not in OCR_MEDIA_TYPES:
            continue
        dst = req_dir / sha
        dst.write_bytes((work / rec.vault_relpath).read_bytes())
        n += 1
    write_manifest(export_dir, export_dir / "_REQUEST-MANIFEST.sha256")
    custody.append("ocr_enclave_exported", {"export_dir": str(export_dir), "requests": n})
    return n


def ocr_import(work: Path, export_dir: Path, custody: CustodyLog) -> int:
    """Verify and ingest enclave OCR responses into work/ocr-raw."""
    work, export_dir = Path(work), Path(export_dir)
    manifest = read_manifest(export_dir / "_REQUEST-MANIFEST.sha256")
    records = load_records(work)
    # request bundle integrity: every exported request must still match
    for rel, digest in manifest.items():
        if rel.startswith("requests/"):
            p = export_dir / rel
            if not p.exists() or sha256_of(p) != digest:
                raise OcrError(f"enclave request bundle tampered: {rel}")
    (work / "ocr-raw").mkdir(exist_ok=True)
    status: dict[str, str] = {}
    n = 0
    for sha in sorted(records):
        rec = records[sha]
        if rec.media_type not in OCR_MEDIA_TYPES:
            status[sha] = "not_applicable"
            continue
        resp = export_dir / "responses" / f"{sha}.json"
        if not resp.exists():
            status[sha] = "ocr_unavailable"
            continue
        raw = resp.read_bytes()
        json.loads(raw)  # must at least be JSON
        (work / "ocr-raw" / f"{sha}.json").write_bytes(raw)
        status[sha] = "succeeded"
        custody.append("ocr_response_stored", {
            "sha256": sha, "adapter": "enclave-import",
            "ocr_raw_sha256": sha256_of_bytes(raw), "status": "succeeded"})
        n += 1
    _write_status(work, "enclave-import", status)
    custody.append("ocr_completed", {"adapter": "enclave-import", "counts": _count(status)})
    return n
