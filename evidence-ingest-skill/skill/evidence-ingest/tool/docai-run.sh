#!/usr/bin/env bash
# docai-run.sh — run the evidence-ingest OCR lane against Google Document AI
# using an Application Default Credentials (ADC) identity impersonating a
# dedicated service account, NOT the operator's owner-scoped user token.
#
# The pipeline itself takes a pre-minted bearer token via --token-file, because
# evidence_ingest/netguard.py pins exactly one hostname for the audited cloud
# exception; doing ADC inside that process would require allowlisting
# oauth2.googleapis.com and iamcredentials.googleapis.com as well, widening the
# very network surface the guard exists to bound. So the token is minted out
# here and handed in.
#
# The token is written to a 0600 file under $TMPDIR, deleted on any exit path,
# and never echoed. Only its sha256 is custody-recorded, by the pipeline.
#
#   ./docai-run.sh --work /path/to/work
#   ./docai-run.sh --work /path/to/work --processor <id> --dry-run
#
# Exit codes: 0 ok · 2 usage/setup · 5 environment unfit · otherwise the
# pipeline's own code (2 gate, 3 custody, 4 network policy).
set -euo pipefail

# Every file this script creates holds or handles a credential.
umask 077

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# No baked-in tenant values: supply the project and service account per
# environment via flags or DOCAI_* env vars. This script ships with empty
# defaults on purpose and refuses to run without them.
SA_DEFAULT=""
PROJECT_DEFAULT=""
LOCATION_DEFAULT="us"
KEYCHAIN_SERVICE="Google Document AI Processor"
KEYCHAIN_ACCOUNT="${DOCAI_KEYCHAIN_ACCOUNT:-}"

WORK=""
SA="${DOCAI_SA:-$SA_DEFAULT}"
PROJECT="${DOCAI_PROJECT:-$PROJECT_DEFAULT}"
LOCATION="${DOCAI_LOCATION:-$LOCATION_DEFAULT}"
PROCESSOR="${DOCAI_PROCESSOR:-}"
IMPERSONATE=1
DRY_RUN=0

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'
info() { printf '%s==>%s %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '%s[warn]%s %s\n' "$YLW" "$RST" "$*" >&2; }
die()  { printf '%s[error]%s %s\n' "$RED" "$RST" "$*" >&2; exit "${2:-2}"; }
step() { printf '%s    %s%s\n' "$DIM" "$*" "$RST"; }

usage() {
    cat <<EOF
usage: docai-run.sh --work DIR [options]

  --work DIR              evidence-ingest work directory (required)
  --processor ID          Document AI processor id
                          (or set DOCAI_KEYCHAIN_ACCOUNT to read a cached id
                          from the macOS Keychain item "$KEYCHAIN_SERVICE")
  --project ID            GCP project id (REQUIRED unless DOCAI_PROJECT is set)
  --location REGION       Document AI region       (default: $LOCATION_DEFAULT)
  --service-account EMAIL impersonation target (REQUIRED when impersonating,
                          unless DOCAI_SA is set)
  --no-impersonate        mint the operator's own user token instead
                          (works only if that identity can call :process, and
                          writes a broader-scoped credential to disk)
  --dry-run               show the pipeline command without minting or running
  -h, --help              this help

Env overrides: DOCAI_SA, DOCAI_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR,
               DOCAI_KEYCHAIN_ACCOUNT
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --work)            WORK="${2:?--work needs a path}"; shift 2 ;;
        --processor)       PROCESSOR="${2:?--processor needs an id}"; shift 2 ;;
        --project)         PROJECT="${2:?--project needs an id}"; shift 2 ;;
        --location)        LOCATION="${2:?--location needs a region}"; shift 2 ;;
        --service-account) SA="${2:?--service-account needs an email}"; shift 2 ;;
        --no-impersonate)  IMPERSONATE=0; shift ;;
        --dry-run)         DRY_RUN=1; shift ;;
        -h|--help)         usage; exit 0 ;;
        *)                 die "unknown option: $1" 2 ;;
    esac
done

# ---------------------------------------------------------------- preflight --
[ -n "$WORK" ] || { usage >&2; die "--work is required" 2; }
[ -d "$WORK" ] || die "work directory does not exist: $WORK" 2
[ -n "$PROJECT" ] || { usage >&2; die "--project (or DOCAI_PROJECT) is required" 2; }
if [ $IMPERSONATE -eq 1 ] && [ -z "$SA" ]; then
    usage >&2
    die "--service-account (or DOCAI_SA) is required when impersonating; or pass --no-impersonate" 2
fi
[ -x "$TOOL_DIR/ingest.sh" ] || die "launcher not found or not executable: $TOOL_DIR/ingest.sh" 5
command -v gcloud >/dev/null 2>&1 \
    || die "gcloud not on PATH — install the Google Cloud CLI and re-run" 5

# Resolve the processor id: explicit flag/env wins; a macOS Keychain lookup is
# attempted only when DOCAI_KEYCHAIN_ACCOUNT is set. The id is not a secret,
# but it is not printed in full.
if [ -z "$PROCESSOR" ]; then
    if [ -n "$KEYCHAIN_ACCOUNT" ]; then
        PROCESSOR="$(security find-generic-password -s "$KEYCHAIN_SERVICE" \
                         -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null || true)"
        [ -n "$PROCESSOR" ] && step "processor id read from Keychain"
    fi
    [ -n "$PROCESSOR" ] \
        || die "no processor id: pass --processor, set DOCAI_PROCESSOR, or set
       DOCAI_KEYCHAIN_ACCOUNT to read Keychain item -s '$KEYCHAIN_SERVICE'" 2
fi
# Some environments cache the full resource name
# (projects/N/locations/us/processors/<id>); the pipeline wants the bare id.
# Accept either form by taking the last path segment.
case "$PROCESSOR" in
    */*) PROCESSOR="${PROCESSOR##*/}" ;;
esac
# Processor ids are lowercase hex; reject anything else before it reaches a URL.
case "$PROCESSOR" in
    *[!0-9a-f]*|"") die "processor id is not lowercase hex: ${PROCESSOR:0:4}…" 2 ;;
esac

info "Document AI OCR lane"
step "project   : $PROJECT"
step "location  : $LOCATION"
step "processor : ${PROCESSOR%${PROCESSOR#????}}… (${#PROCESSOR} chars)"
if [ $IMPERSONATE -eq 1 ]; then
    step "identity  : impersonating $SA"
else
    warn "identity  : operator user token (--no-impersonate) — broader scope on disk"
fi
step "work      : $WORK"

if [ $DRY_RUN -eq 1 ]; then
    info "Dry run — no token minted, nothing sent"
    printf '%s\n' "\"$TOOL_DIR/ingest.sh\" ocr --work \"$WORK\" \\
    --google-docai --allow-cloud-ocr \\
    --project \"$PROJECT\" --location \"$LOCATION\" \\
    --processor \"$PROCESSOR\" --token-file <0600 tempfile>"
    exit 0
fi

# ----------------------------------------------------------------- token ----
TOKEN_FILE="$(mktemp "${TMPDIR:-/tmp}/docai-token.XXXXXX")"
cleanup() { rm -f "$TOKEN_FILE"; }
trap cleanup EXIT HUP INT TERM

info "Minting access token"
if [ $IMPERSONATE -eq 1 ]; then
    gcloud auth print-access-token --impersonate-service-account="$SA" \
        > "$TOKEN_FILE" 2>/dev/null \
      || die "token mint failed. Confirm ADC is configured:
       gcloud auth application-default login --impersonate-service-account=$SA" 5
else
    gcloud auth print-access-token > "$TOKEN_FILE" 2>/dev/null \
      || die "token mint failed. Run: gcloud auth login" 5
fi
[ -s "$TOKEN_FILE" ] || die "token file is empty after mint" 5
step "token minted to a 0600 tempfile; valid roughly 60 minutes from now"

# ------------------------------------------------------------------- run ----
info "Running OCR lane"
rc=0
"$TOOL_DIR/ingest.sh" ocr --work "$WORK" \
    --google-docai --allow-cloud-ocr \
    --project "$PROJECT" --location "$LOCATION" \
    --processor "$PROCESSOR" --token-file "$TOKEN_FILE" || rc=$?

if [ $rc -ne 0 ]; then
    warn "OCR lane exited $rc"
    warn "If this ran past the token's ~60-minute lifetime, the adapter reads the"
    warn "token once at construction and cannot refresh it. Re-running mints a"
    warn "fresh token, but run_ocr() reprocesses every record from the start —"
    warn "it does not skip pages already written to <work>/ocr-raw/."
    exit $rc
fi

info "OCR lane complete"
