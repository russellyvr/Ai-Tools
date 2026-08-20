"""Pydantic v2 data contracts for evidence-ingest.

Every model uses ``extra="forbid"`` — unknown fields are schema violations,
which is itself a tamper-detection surface (the contortionist red-team agent
proves it). All artifacts are serialized as canonical JSON so their hashes
are reproducible.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"

MediaType = Literal["pdf", "png", "jpeg", "tiff", "bmp", "eml", "txt",
                    "csv", "html", "xlsx", "xls", "docx", "doc", "other"]
Channel = Literal["native-text", "azure-read-3.2", "google-docai-v1", "none"]

# Drop-ledger reason codes (fail-closed accounting: every input file is
# either an accepted occurrence or a drop with one of these codes).
REASON_SYMLINK = "SYMLINK_REJECTED"
REASON_REPARSE = "REPARSE_POINT_REJECTED"
REASON_NOT_REGULAR = "NOT_REGULAR_FILE"
REASON_SOURCE_CHANGED = "SOURCE_CHANGED_DURING_CAPTURE"
REASON_COPY_MISMATCH = "TAMPER_COPY_MISMATCH"
REASON_MAGIC_MISMATCH = "TAMPER_MAGIC_MISMATCH"
REASON_TRUNCATED = "TAMPER_TRUNCATED"
REASON_TRAILING = "TAMPER_TRAILING_DATA"
REASON_TOO_LARGE = "RESOURCE_TOO_LARGE"
REASON_EMPTY = "RESOURCE_EMPTY"
REASON_UNCONFINED = "PATH_UNCONFINED"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunConfig(StrictModel):
    """Run configuration; its canonical-JSON sha binds the stage gates."""

    schema_version: str = SCHEMA_VERSION
    max_file_bytes: int = 500 * 1024 * 1024
    chunk_target: int = 2000
    chunk_overlap: int = 200
    ocr_mode: Literal["pending", "none", "azure-read", "google-docai", "enclave"] = "pending"
    tool_version: str = ""


class Occurrence(StrictModel):
    """One appearance of a content sha at a source path (dedup preserves all)."""

    relpath: str
    size_bytes: int
    mtime_utc: str


class EvidenceRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int
    media_type: MediaType
    magic_label: str
    vault_relpath: str
    occurrences: list[Occurrence]
    captured_utc: str
    capture_warnings: list[str] = Field(default_factory=list)


class DropRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    relpath: str
    reason_code: str
    detail: str
    utc: str


class EmailRecipient(StrictModel):
    role: Literal["from", "sender", "reply_to", "to", "cc", "bcc"]
    display_name: Optional[str] = None
    address: str
    raw: str


class Page(StrictModel):
    page_number: Optional[int] = None
    text: str


class TableMeta(StrictModel):
    """Shape metadata for one tabular unit (a CSV file or one worksheet)."""

    name: str                 # sheet name, or "csv" for a CSV file
    page_number: int          # the Page this table was serialized into
    rows: int
    cols: int


class ExtractionBundle(StrictModel):
    schema_version: str = SCHEMA_VERSION
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: MediaType
    channel: Channel
    pages: list[Page]
    parse_warnings: list[str] = Field(default_factory=list)
    # email metadata (subject doubles as the <title> for html documents)
    subject: Optional[str] = None
    date_raw: Optional[str] = None
    message_id: Optional[str] = None
    recipients: list[EmailRecipient] = Field(default_factory=list)
    raw_headers: dict[str, list[str]] = Field(default_factory=dict)
    ocr_raw_sha256: Optional[str] = None
    # tabular-only fields (csv/xlsx)
    tables_meta: list[TableMeta] = Field(default_factory=list)
    tool_version: str


class Embedding(StrictModel):
    state: Literal["not_generated"] = "not_generated"
    model_id: Optional[str] = None
    dim: Optional[int] = None
    vector: Optional[list[float]] = None


class RagChunk(StrictModel):
    schema_version: str = SCHEMA_VERSION
    chunk_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str
    source_relpaths: list[str]
    media_type: MediaType
    channel: Channel
    page_number: Optional[int] = None
    char_start: int
    char_end: int
    utf8_byte_start: int
    utf8_byte_end: int
    text: str
    text_sha256: str
    extraction_sha256: str
    chunk_config_sha256: str
    tool_version: str
    code_tree_sha256: str
    run_id: str
    embedding: Embedding = Field(default_factory=Embedding)


class CustodyEvent(StrictModel):
    sequence: int
    utc: str
    event: str
    details: dict
    prev_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
