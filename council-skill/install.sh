#!/usr/bin/env bash
#
# install.sh — installs the "council" skill for GitHub Copilot CLI (macOS).
#
# Copies skill/council from this package into the Copilot CLI skills folder
# ($HOME/.copilot/skills/council by default; override with COPILOT_HOME).
#
# Design & security notes:
#   - Runs entirely as the current user. NO sudo required or requested.
#   - Makes NO network calls, downloads nothing, executes nothing from the
#     package — it only copies documented text files.
#   - Never touches settings.json, copilot-instructions.md, or any other
#     configuration; it only writes inside the target skill folder.
#   - Idempotent: safe to re-run. An existing installation is backed up to
#     a timestamped sibling folder before being replaced.
#   - Compatible with macOS's stock bash 3.2 (no bash-4+ features).
#
# Usage:
#   ./install.sh
#   COPILOT_HOME="$HOME/.copilot" ./install.sh
#
set -euo pipefail
umask 077   # new files are private to the current user

SKILL_NAME="council"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
SOURCE="$SCRIPT_DIR/skill/$SKILL_NAME"
COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
TARGET="$COPILOT_HOME/skills/$SKILL_NAME"

# --- Preflight: validate the package before touching anything --------------
[ -f "$SOURCE/SKILL.md" ] || {
    echo "ERROR: '$SOURCE/SKILL.md' not found. Run this script from the extracted package root." >&2
    exit 1
}
for ref in prompts.md rubric.md output-template.md; do
    [ -f "$SOURCE/references/$ref" ] || {
        echo "ERROR: package is incomplete: references/$ref is missing." >&2
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
[ -f "$TARGET/SKILL.md" ] || {
    echo "ERROR: installation verification failed: SKILL.md missing at target." >&2
    exit 1
}

echo
echo "Installed: $TARGET"
echo
echo "Next steps:"
echo "  1. Restart any running GitHub Copilot CLI session."
echo "  2. Invoke the skill:  /council <your question or decision>"
echo "  3. If your model list differs from the shipped roster"
echo "     (Claude Fable 5 / Gemini 3.1 Pro / GPT-5.6 Sol), edit the"
echo "     roster table in $TARGET/SKILL.md."
