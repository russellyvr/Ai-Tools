#!/usr/bin/env bash
#
# install.sh — installs the "evidence-ingest" skill (macOS / Linux).
#
# Copies skill/evidence-ingest from this package into the skills folder of the
# CLI you choose:
#   ./install.sh --claude    → $HOME/.claude/skills/evidence-ingest
#   ./install.sh --copilot   → $HOME/.copilot/skills/evidence-ingest
# Override the CLI home with CLAUDE_HOME / COPILOT_HOME.
#
# Design & security notes:
#   - Runs entirely as the current user. NO sudo required or requested.
#   - Makes NO network calls, downloads nothing, executes nothing from the
#     package — it only copies documented text files.
#   - Never touches settings, instructions files, or any other configuration;
#     it only writes inside the target skill folder.
#   - Idempotent: safe to re-run. An existing installation is backed up to
#     a timestamped sibling folder before being replaced.
#   - Compatible with macOS's stock bash 3.2 (no bash-4+ features).
#
# After installing, provision the tool's virtualenv once (see README.md):
#   cd <target>/tool && python3 -m venv .venv \
#     && .venv/bin/pip install "pydantic>=2.5,<3" python-docx openpyxl
#
set -euo pipefail
umask 077   # new files are private to the current user

SKILL_NAME="evidence-ingest"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
SOURCE="$SCRIPT_DIR/skill/$SKILL_NAME"

usage() {
    echo "usage: install.sh --claude | --copilot" >&2
    echo "  --claude    install for Claude Code   (\$HOME/.claude/skills/)" >&2
    echo "  --copilot   install for Copilot CLI   (\$HOME/.copilot/skills/)" >&2
    exit 2
}

TARGET=""
case "${1:-}" in
    --claude)  TARGET="${CLAUDE_HOME:-$HOME/.claude}/skills/$SKILL_NAME" ;;
    --copilot) TARGET="${COPILOT_HOME:-$HOME/.copilot}/skills/$SKILL_NAME" ;;
    *)         usage ;;
esac
[ $# -eq 1 ] || usage

# --- Preflight: validate the package before touching anything --------------
[ -f "$SOURCE/SKILL.md" ] || {
    echo "ERROR: '$SOURCE/SKILL.md' not found. Run this script from the extracted package root." >&2
    exit 1
}
for f in tool/ingest.sh tool/evidence_ingest/__init__.py tool/evidence_ingest/cli.py tool/demo/run-demo.sh; do
    [ -f "$SOURCE/$f" ] || {
        echo "ERROR: package is incomplete: $f is missing." >&2
        exit 1
    }
done

# --- Backup any existing installation ---------------------------------------
if [ -e "$TARGET" ]; then
    BACKUP="$TARGET.bak-$(date +%Y%m%d-%H%M%S)"
    mv -- "$TARGET" "$BACKUP"
    echo "Backed up existing installation to: $BACKUP"
fi

# --- Install -----------------------------------------------------------------
mkdir -p -- "$(dirname -- "$TARGET")"
cp -R -- "$SOURCE" "$TARGET"

# Verify the copy landed intact.
[ -f "$TARGET/SKILL.md" ] && [ -x "$TARGET/tool/ingest.sh" ] || {
    echo "ERROR: installation verification failed at target." >&2
    exit 1
}

echo
echo "Installed: $TARGET"
echo
echo "Next steps:"
echo "  1. Provision the tool virtualenv (one time):"
echo "       cd \"$TARGET/tool\" && python3 -m venv .venv \\"
echo "         && .venv/bin/pip install \"pydantic>=2.5,<3\" python-docx openpyxl"
echo "  2. Restart any running CLI session so it picks up the skill."
echo "  3. Smoke-test without OCR or network:"
echo "       \"$TARGET/tool/demo/run-demo.sh\""
