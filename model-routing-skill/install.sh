#!/usr/bin/env bash
#
# install.sh — installs the deterministic model-routing deployment for
# GitHub Copilot CLI (macOS): KPI analyzer, targets, and the full spec.
#
# Copies into the Copilot CLI home ($HOME/.copilot by default; override
# with COPILOT_HOME):
#   routing/analyze_routing.py    -> <home>/routing/
#   routing/targets.json          -> <home>/routing/  (never overwritten if present)
#   instructions/model-routing.md -> <home>/instructions/
#
# Design & security notes:
#   - Runs entirely as the current user. NO sudo required or requested.
#   - Makes NO network calls, downloads nothing, executes nothing — it only
#     copies documented text files. The analyzer is a standard-library-only
#     Python script you can read before running.
#   - DELIBERATELY never edits settings.json or copilot-instructions.md:
#     model pins and the inline rubric change your agent's behavior, so
#     those steps stay manual and are printed at the end.
#   - Your existing targets.json (your KPI targets) is never overwritten;
#     the packaged copy is written alongside as targets.json.new instead.
#   - Idempotent and backup-first. Compatible with macOS's stock bash 3.2.
#
# Usage:
#   ./install.sh
#   COPILOT_HOME="$HOME/.copilot" ./install.sh
#
set -euo pipefail
umask 077   # new files are private to the current user

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
STAMP="$(date +%Y%m%d-%H%M%S)"

# --- Preflight ----------------------------------------------------------------
for f in "$SCRIPT_DIR/routing/analyze_routing.py" \
         "$SCRIPT_DIR/routing/targets.json" \
         "$SCRIPT_DIR/instructions/model-routing.md"; do
    [ -f "$f" ] || {
        echo "ERROR: '$f' not found. Run this script from the extracted package root." >&2
        exit 1
    }
done
command -v python3 >/dev/null 2>&1 || \
    echo "WARNING: python3 not found on PATH. The analyzer needs Python 3.9+." >&2

# install_file <src> <dst> [never_overwrite]
install_file() {
    src="$1"; dst="$2"; never="${3:-no}"
    mkdir -p -- "$(dirname -- "$dst")"
    if [ -e "$dst" ] && [ "$never" = "yes" ]; then
        cp -- "$src" "$dst.new"
        echo "Kept your existing $(basename -- "$dst"); packaged version saved as $(basename -- "$dst").new"
        return 0
    fi
    if [ -e "$dst" ]; then
        cp -- "$dst" "$dst.bak-$STAMP"
        echo "Backed up existing $(basename -- "$dst") to $(basename -- "$dst").bak-$STAMP"
    fi
    cp -- "$src" "$dst"
    echo "Installed: $dst"
}

# --- Install --------------------------------------------------------------------
install_file "$SCRIPT_DIR/routing/analyze_routing.py"    "$COPILOT_HOME/routing/analyze_routing.py"
install_file "$SCRIPT_DIR/routing/targets.json"          "$COPILOT_HOME/routing/targets.json" yes
install_file "$SCRIPT_DIR/instructions/model-routing.md" "$COPILOT_HOME/instructions/model-routing.md"

cat <<EOF

Files installed.

Manual steps (deliberately NOT automated - these change agent behavior):
  1. Pin your sub-agents in ~/.copilot/settings.json -> "subagents": { "agents": { ... } }
     explore/task = a cheap ECONOMY model at low effort;
     code-review/research = a STANDARD model at medium effort.
  2. Paste the compact 7-row routing table (see README or the spec)
     into ~/.copilot/copilot-instructions.md so it is injected every turn.
  3. Edit tier_patterns in ~/.copilot/routing/targets.json to match
     the model names visible in YOUR session.
  4. Test the analyzer:  python3 "\$HOME/.copilot/routing/analyze_routing.py"
  5. Optional: install the companion route-tune skill for the
     self-tuning feedback loop.
EOF
