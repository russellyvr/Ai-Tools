#!/usr/bin/env bash
#
# install.sh — installs the "route-tune" skill for GitHub Copilot CLI (macOS).
#
# Copies skill/route-tune from this package into the Copilot CLI skills
# folder ($HOME/.copilot/skills/route-tune by default; override with
# COPILOT_HOME).
#
# PREREQUISITE: the model-routing deployment (companion package) must be
# installed first — route-tune is the tuner for that deployment and needs
# <home>/routing/analyze_routing.py and targets.json to exist. This script
# checks and warns, but does not install them.
#
# Design & security notes:
#   - Runs entirely as the current user. NO sudo required or requested.
#   - Makes NO network calls, downloads nothing, executes nothing — it only
#     copies documented text files.
#   - Never touches settings.json, copilot-instructions.md, or the routing
#     assets; it only writes inside the target skill folder. (The skill
#     itself edits pins only within bounded, logged, reversible limits —
#     see SKILL.md.)
#   - Idempotent and backup-first. Compatible with macOS's stock bash 3.2.
#
# Usage:
#   ./install.sh
#   COPILOT_HOME="$HOME/.copilot" ./install.sh
#
set -euo pipefail
umask 077   # new files are private to the current user

SKILL_NAME="route-tune"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
SOURCE="$SCRIPT_DIR/skill/$SKILL_NAME"
COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
TARGET="$COPILOT_HOME/skills/$SKILL_NAME"

# --- Preflight ------------------------------------------------------------------
[ -f "$SOURCE/SKILL.md" ] || {
    echo "ERROR: '$SOURCE/SKILL.md' not found. Run this script from the extracted package root." >&2
    exit 1
}
for dep in "$COPILOT_HOME/routing/analyze_routing.py" "$COPILOT_HOME/routing/targets.json"; do
    [ -f "$dep" ] || {
        echo "WARNING: prerequisite missing: $dep" >&2
        echo "         Install the companion model-routing package first - route-tune cannot run without it." >&2
    }
done

# --- Backup any existing installation ----------------------------------------------
if [ -e "$TARGET" ]; then
    BACKUP="$TARGET.bak-$(date +%Y%m%d-%H%M%S)"
    mv -- "$TARGET" "$BACKUP"
    echo "Backed up existing installation to: $BACKUP"
fi

# --- Install --------------------------------------------------------------------------
mkdir -p -- "$(dirname -- "$TARGET")"
cp -R -- "$SOURCE" "$TARGET"

[ -f "$TARGET/SKILL.md" ] || {
    echo "ERROR: installation verification failed: SKILL.md missing at target." >&2
    exit 1
}

cat <<EOF

Installed: $TARGET

Next steps:
  1. Ensure the model-routing deployment is installed (analyzer + targets).
  2. Restart any running GitHub Copilot CLI session.
  3. Run an interactive review:      /route-tune
     Or apply the recommendation:    /route-tune go
  4. Recommended: schedule the analyzer weekly (cron or launchd) so the KPI
     report is fresh when you review it. The analyzer only measures - it
     never tunes. Example crontab entry, Mondays at 09:00:
       0 9 * * 1  python3 "\$HOME/.copilot/routing/analyze_routing.py"
  5. Then run /route-tune once a week and decide what to apply. Nothing in
     this skill runs on its own - it acts only when you invoke it.
EOF
