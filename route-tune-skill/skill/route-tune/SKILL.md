---
name: route-tune
description: Review and tune the self-improving model-routing deployment - runs the deterministic KPI analyzer (.copilot\routing\analyze_routing.py), compares results to targets.json, and applies bounded, logged, reversible changes to subagent model/effort pins in settings.json. Use when the user asks about model cost, token usage, routing effectiveness, subagent model pins, escalation rates, or wants a weekly routing review. Invoke as "/route-tune" (interactive review) or "/route-tune go" (apply the recommended bounded change autonomously).
---

# route-tune - Self-Improving Model Routing

## Purpose

Review model-routing efforts and results, then apply **bounded, logged,
reversible** improvements to the routing deployment. This is the closed
feedback loop for the routing system: measure -> diagnose -> tune one step ->
verify next cycle -> revert on regression.

Invoke as `/route-tune` (interactive review) or `/route-tune go`
(apply the recommended bounded change autonomously).

This skill is **manually run**. It has no scheduler, no background process and
no trigger of its own - a cycle happens only when a human types the command.
`/route-tune go` skips the confirmation step *within that run*; it does not make
the skill autonomous.

## Assets (all under `%USERPROFILE%\.copilot\`)

| Path | Role |
|---|---|
| `routing\analyze_routing.py` | Deterministic KPI analyzer (LLM-free) |
| `routing\targets.json` | KPI targets, tier patterns, pin bounds |
| `routing\state.json` | KPI snapshot history (trend memory) |
| `routing\report-latest.md` | Latest generated report |
| `routing\CHANGELOG.md` | Every tuning action, append-only |
| `settings.json` -> `subagents.agents` | Live per-subagent model/effort pins |
| `copilot-instructions.md` (routing section) | Ambient inline rubric |
| `instructions\model-routing.md` | Full spec (reference doc) |

## Procedure

### 1. Measure

Run `python "%USERPROFILE%\.copilot\routing\analyze_routing.py"` (default
window from targets.json). Read `report-latest.md` and the last few
snapshots in `state.json` for trend direction. Exit code 1 = KPI breach.

### 2. Diagnose (map breach -> lever)

| Signal | Diagnosis | Lever |
|---|---|---|
| `subagent_escalation_rate` > max | Pins too cheap; work failing at ECONOMY | Raise the offending agent-type pin ONE class (within `pin_bounds`) |
| escalation ~0% AND economy share high AND quality complaints absent for 2+ cycles | Pins may be safely lowered / effort reduced | Lower pin one class or effort one step (within bounds) |
| `economy_share_of_mechanical_dispatches` < min | Dispatches overriding pins with expensive models | Strengthen inline rubric wording; check for skills mis-pinning |
| `mechanical_dispatches` near zero while main model does greppy/verbose work | Under-delegation | Adjust rubric delegation trigger (e.g. "delegate when verbose output or >5 tool calls expected") |
| `avg_main_weighted_input_per_turn` > max (cache-weighted: uncached 1.0, cache_write 1.25, cache_read 0.1) | Context bloat | Advise user: /clear /new /compact cadence; agent-side: view_range discipline, route verbose output through task agent |
| `frontier_cost_share` > max AND main-role dominates cost | Session default model too high | ADVISE ONLY - recommend user change `settings.json` model or use `/model`; never change the user's session model autonomously |

### 3. Tune (bounded self-modification)

Rules - HARD LIMITS on self-modification:
- At most ONE pin change AND one rubric wording refinement per cycle.
- Pin changes move exactly ONE tier class per cycle and must stay within
  `pin_bounds` in targets.json.
- NEVER touch: `general-purpose`/`security-review` pins (stay `inherit`),
  the row-7 frontier floor, the high-stakes override, or any non-routing
  section of copilot-instructions.md or settings.json.
- KPI *targets* in targets.json may only be changed by the user, except the
  analyzer window and tier_patterns (may be updated when the live model
  list changes names).
- Every change gets a CHANGELOG.md entry: date, KPI evidence, exact
  before/after, expected effect, and the revert condition.
- **Provenance discipline:** externally-sourced changes (cross-machine
  syncs, user-directed edits) are logged but do NOT consume the
  one-change-per-cycle budget and are EXEMPT from revert/cool-down logic.
  Only the tuner's own autonomous changes are subject to verify-and-revert
  — otherwise the heuristic blames a sync for a KPI move it didn't cause.
- Back up settings.json before editing it.

### 4. Verify & revert (next cycle)

At the start of each run, check CHANGELOG.md for the most recent change:
- If the KPI it targeted improved or held: mark it `VERIFIED` in the log.
- If the KPI regressed or a new quality breach appeared (escalation rate
  jumped past max): REVERT the change exactly, mark `REVERTED`, and do not
  retry the same change for 3 cycles.

### 5. Report

Summarize to the user: KPI table, trend vs last cycle, action taken (or
"no change warranted"), and any user-only levers (session model choice,
context hygiene) with expected savings. Keep it under ~200 words unless
asked for detail. End with an explicit recommendation the user can accept or
decline - the point of the cycle is to surface a decision, not to have already
made it.

## Cadence

Schedule the *analyzer* weekly so `report-latest.md` is always fresh - a Task
Scheduler task named `CopilotRoutingAnalyzer` on Windows, cron or a launchd
agent on macOS/Linux. That job is LLM-free and read-only: it measures, it never
tunes.

The tuning cycle itself is manual. Run `/route-tune` whenever the user asks
about cost, or at least weekly once the fresh report has landed. The skill is
idempotent - re-running without new data makes no change.
