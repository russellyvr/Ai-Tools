# route-tune — bounded self-tuning for Copilot CLI model routing

The self-tuning half of a deterministic model-routing deployment for GitHub
Copilot CLI. `/route-tune` runs the deployment's LLM-free KPI analyzer,
compares results to user-owned targets, applies **at most one bounded,
logged, reversible change per cycle**, verifies it against the next cycle's
KPIs, and reverts itself on regression.

Published for the general public: the goal is to help anyone running an
agentic CLI save real money/quota on LLM tokens without losing output
quality — with every design decision traceable to a measurement (sound
provenance, documented below).

Full documentation: [`docs/index.html`](docs/index.html) (GitHub Pages).

## How it runs

route-tune is a **manually run skill**. There is no daemon, no watcher and no
timer — nothing happens until you type `/route-tune` in a Copilot CLI session.
Even `/route-tune go`, which applies the recommended change without stopping to
ask, only ever runs because a human started it.

The one piece worth automating is the **analyzer**: standard-library Python,
LLM-free, read-only. It measures; it never tunes. Schedule it weekly so the KPI
report is already fresh when you sit down to review.

```sh
# macOS / Linux — crontab -e, Mondays at 09:00
0 9 * * 1  python3 "$HOME/.copilot/routing/analyze_routing.py"
```

```powershell
# Windows — PowerShell 7, weekly on Monday
$a = New-ScheduledTaskAction -Execute 'python' -Argument "`"$HOME\.copilot\routing\analyze_routing.py`""
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
Register-ScheduledTask -TaskName 'CopilotRoutingAnalyzer' -Action $a -Trigger $t
```

On macOS you can use a launchd agent with a `StartCalendarInterval` instead of
cron; it runs the same one-line command.

Then make the review itself the weekly habit: run `/route-tune`, read the KPI
table and the single change it proposes, and decide. The measurement is
automated; the judgement stays yours. When routing is healthy the answer is
"no change warranted" and you are done in under a minute.

## Install

```sh
# macOS
./install.sh

# Windows (PowerShell 7+)
pwsh -File .\install.ps1        # add -WhatIf to preview
```

Installers run as the current user only, make no network calls, download
nothing, and never touch `settings.json` or your instructions — they copy the
skill folder, backup-first, and print next steps. Manual equivalent:
`cp -r skill/route-tune ~/.copilot/skills/route-tune`.

Paths inside `SKILL.md` are written as `%USERPROFILE%\.copilot\…`; on
macOS/Linux read them as `~/.copilot/…`.

## Prerequisites

- **The companion [model-routing](../model-routing-skill/) deployment**
  (analyzer, `targets.json`, routing spec, sub-agent pins). Install it first —
  route-tune measures and tunes *that* system.
- GitHub Copilot CLI with custom-skill support (`~/.copilot/skills/`).
- Python 3.9+ (analyzer is standard-library only; all measurement is local —
  nothing leaves the machine).
- Recommended: a weekly scheduled analyzer run (Task Scheduler / launchd / cron)
  so the report is fresh when you review it — see [How it runs](#how-it-runs).

## Hard limits on self-modification

- Max one pin change + one rubric-wording refinement per cycle; pin moves are
  one tier class, inside `pin_bounds`.
- Untouchable: general-purpose/security-review pins, the frontier floor on
  high-stakes work, KPI targets (user-owned), and all non-routing config.
- Append-only changelog with evidence, before/after, and revert condition;
  `settings.json` backed up before any edit.
- Verify-and-revert next cycle; 3-cycle cool-down after any revert.
- External/user changes are logged but exempt from the change budget and
  revert logic (provenance discipline).

## Layout

| Path | Purpose |
|---|---|
| `skill/route-tune/SKILL.md` | The tuning skill: measure → diagnose → bounded tune → verify/revert → report |
| `install.ps1` / `install.sh` | Current-user, backup-first installers (Windows PS7 / macOS bash) |
| `docs/index.html` | GitHub Pages documentation |

## Method & cost discipline

This skill exists to keep a token-saving deployment saving tokens without
anyone having to babysit it — and to do that at effectively zero token cost
itself. The entire measurement path is LLM-free: the analyzer is
standard-library Python reading local session data, so a tuning cycle spends
nothing to find out whether the last change helped. The one-change-per-cycle
budget, the `pin_bounds` clamp, the append-only changelog and the
verify-and-revert rule are all there for the same reason — an autonomous tuner
that drifts is worse than no tuner at all, because it degrades output quality
while appearing to optimize.

The self-improvement protocol, its hard limits, and the diagnosis map were
deliberated across an AI council spanning three independent vendors, each
answering independently before anonymized cross-review:

| Vendor | Frontier model |
|---|---|
| Anthropic | Claude Fable 5 |
| Google | Gemini 3.1 Pro |
| OpenAI | GPT-5.6 Sol |

That pass is what produced the "cannot game its own metrics" property: a
tuner scored against KPIs it is also allowed to redefine will always converge
on flattering numbers, so KPI targets were made user-owned and untouchable.
Claims here are grounded in primary documentation and published prior art
rather than model recall — the derivations follow.

## Sources & derivation

- **Primary — original iterative engineering:** the self-improvement protocol
  of model-routing spec v3.x, added after two measurably failed generations
  (v1 hardcoded names → stale; v2 advisory prose → non-compliance) and
  hardened via cross-machine peer review between two independent live
  deployments. Full lineage ships in the companion package's
  `instructions/model-routing.md`.
- **Platform:** [GitHub Copilot CLI documentation](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli).
- **Related prior art (context, not derivation):**
  [FrugalGPT (arXiv:2305.05176)](https://arxiv.org/abs/2305.05176),
  [RouteLLM (arXiv:2406.18665)](https://arxiv.org/abs/2406.18665) — learned
  difficulty routing; this system routes by verifiability and dispatch
  surface so the deterministic tuner cannot game its own metrics.
