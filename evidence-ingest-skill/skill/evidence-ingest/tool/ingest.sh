#!/usr/bin/env bash
# ingest.sh — thin macOS (Apple Silicon) launcher for evidence-ingest (corpus mode).
# Usage: ./ingest.sh <evidence_ingest args...>
#
# Launcher-only extra (Ring 1, never passed to Python): `run ... --clean`
#   After a successful `run`, the launcher re-verifies the output
#   (`verify --output O`) and, only if verify passes, deletes the staging
#   work folder EXCEPT `_improve/` (the self-improvement issue log is kept).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Prefer the installer-created virtualenv; fall back to system python3.
if [[ -x "$root/.venv/bin/python3" ]]; then
    PY="$root/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "python3 not found on PATH (3.11+ required)" >&2; exit 5
fi
"$PY" - <<'EOF' || { echo "Python 3.11+ required" >&2; exit 5; }
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
EOF

# Intercept launcher-only --clean flag (valid only with the `run` command).
clean=0
fwd=()
for a in "$@"; do
    if [[ "$a" == "--clean" ]]; then clean=1; else fwd+=("$a"); fi
done
if [[ $clean -eq 1 && ( ${#fwd[@]} -eq 0 || "${fwd[0]}" != "run" ) ]]; then
    echo "--clean is only supported with the 'run' command" >&2; exit 2
fi

# Resolve --output and --work (work defaults to '<output>-work' beside it).
out_dir=""; work_dir=""
for ((i = 0; i < ${#fwd[@]} - 1; i++)); do
    [[ "${fwd[$i]}" == "--output" ]] && out_dir="${fwd[$((i + 1))]}"
    [[ "${fwd[$i]}" == "--work" ]] && work_dir="${fwd[$((i + 1))]}"
done
if [[ $clean -eq 1 && -z "$out_dir" ]]; then
    echo "--clean requires --output" >&2; exit 2
fi
[[ $clean -eq 1 && -z "$work_dir" ]] && work_dir="${out_dir}-work"

cd "$root"
if [[ $clean -eq 0 ]]; then
    exec "$PY" -m evidence_ingest "${fwd[@]}"
fi

"$PY" -m evidence_ingest "${fwd[@]}"

# Gate cleanup on a fresh full verify of the published output.
rc=0
"$PY" -m evidence_ingest verify --output "$out_dir" || rc=$?
if [[ $rc -ne 0 ]]; then
    echo "verify failed (exit $rc) — work folder retained: $work_dir" >&2
    exit $rc
fi
if [[ -d "$work_dir" ]]; then
    find "$work_dir" -mindepth 1 -maxdepth 1 ! -name '_improve' -exec rm -rf {} +
    echo "cleaned work folder (kept _improve): $work_dir"
fi
exit 0
