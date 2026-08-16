# Deterministic Model Routing Specification (Cost-Optimal, Zero Fidelity Loss)

Version: 3.1 (2026-08-13)
Lineage: v1.0 → v2.x (advisory prose era) → **v3.0 (2026-08-12) structural
+ self-improving**: routing moved from advisory prose into `settings.json`
`subagents.agents` pins (defaults, not caps); compact rubric inlined into
`copilot-instructions.md`; the per-batch RE-READ rule deleted (measured
non-compliance: 15 ECONOMY turns in 14 days, 86% frontier cost share); the
"session model is the cost ceiling" rule deleted (a cheap main session must
be free to escalate UP); closed measurement/tuning loop added (see
"Self-improvement protocol") → **v3.1 cross-machine fixes** from a peer deployment on a second machine
response (peer-review response document):

1. Cache-aware context KPI — raw input/turn was ~92% cache reads billed at
   0.1×; the KPI now weights tokens by price class (uncached 1.0 /
   cache_write 1.25 / cache_read 0.1; true weighted baseline ≈ 15K/turn,
   not 77K).
2. "Mechanical" is classified by dispatch surface (agent_type in the event
   log), never by intent prose — a denominator the tuner cannot game.
3. Savings denominate in nano-AIU/quota headroom, not dollars
   (subscription billing) — stated in targets.json.
4. Enforcement bound: any deny-capable hook may deny only unambiguous
   violations (frontier model explicitly set on a known-mechanical agent
   type), must log everything, and fails open on doubt — a deterministic
   script cannot grade prompt hardness.
5. Evidence citation: the definitive prose-vs-config proof is the peer deployment's
   natural experiment (13 pinned subagent definitions → 834 STANDARD
   sidechain messages vs. prose-routed ECONOMY rows → 0 messages in the
   same sessions over 14 days), replacing this machine's
   small-n/council-contaminated ~69-dispatch sample.

Scope: every session, every turn, every repository. This file is REFERENCE
documentation; the operative rubric is the inline table in
`copilot-instructions.md` and the pins in `settings.json`.

## Objective

At every turn, before delegating any work via the `task` tool or selecting a
`reasoning_effort`, deterministically select the lowest-cost model tier that
provably loses no fidelity or quality. Token spend is optimized continuously;
quality is protected by verifiability rules and an escalation ladder, never
by guesswork.

## Tier classes (resolve at runtime — never hardcode model names)

- **ECONOMY** — cheapest mini/flash/haiku class in the CURRENT model list.
- **STANDARD** — mid sonnet/mini-pro class.
- **FRONTIER** — the top-capability class in the live session's model list.
  (v3.0: the old "session model = cost ceiling" rule is DELETED. When the
  main session runs a STANDARD-class daily driver, row-6/7 work must still
  dispatch to a FRONTIER model — escalation up is the point.)

Always pick the cheapest available member of the required class. Model lists
change; class definitions don't. (v1 hardcoded names and went stale — do not
regress.)

## Core principle: verifiability-first

Cheap routing is lossless only when correctness is machine-checkable or the
task is mechanical/extractive. Route by objective task features, not
intuition:

- **Verifiable** — output validated by tests, compiler, linter, schema,
  diff-check, or exact-match criteria. Cheap model + verification loop equals
  frontier fidelity by construction.
- **Extractive** — the answer already exists in files/output; the model only
  finds, lists, or summarizes it.
- **Generative + unverifiable** — judgment, architecture, ambiguity, security
  reasoning. Stays FRONTIER.

## Routing table (deterministic — first match, top to bottom)

| # | Task signature (objective features) | Tier | Copilot CLI dispatch | Effort |
|---|-------------------------------------|------|----------------------|--------|
| 1 | Run command/test/build/lint, report pass-fail; file ops, grep/collate, formatting, JSON/schema shaping, log parsing, mirroring | ECONOMY | `task` agent (default model) | low |
| 2 | File/symbol search, globbing, locating code ("where is X") | ECONOMY | `explore` agent (default model) | low |
| 3 | Summarize/extract from existing text, logs, or diffs | ECONOMY (STANDARD when volume or nuance is high) | ECONOMY-class model | low/minimal |
| 4 | Mechanical single-file edit with machine-verifiable result (rename, format conversion, boilerplate, config change validated by build/lint/tests) | STANDARD | STANDARD-class model | low–medium |
| 5 | Docs/comments from complete existing source; multi-file pattern-repetitive change WITH full test coverage; routine research, drafting, straightforward review | STANDARD | STANDARD-class model | medium |
| 6 | Debugging, root-cause analysis, non-trivial algorithm/design, multi-file refactor WITHOUT full test coverage | FRONTIER | FRONTIER-class model | high |
| 7 | Adversarial/hostile gates, security-sensitive work, architecture, ambiguous multi-constraint tradeoffs, cross-corpus synthesis, irreversible/destructive operations, user-facing final synthesis | FRONTIER | FRONTIER-class model (or council) | max (FLOOR) |

Tie-breakers (apply in order):

1. Doubt between two tiers AND the result is machine-verifiable → take the
   LOWER tier (the escalation ladder protects you).
2. Not machine-verifiable → take the HIGHER tier.
3. Errors hard to reverse (deletes, pushes, sends, schema migrations) →
   FRONTIER regardless of other features.

High-stakes override: when correctness is safety/legal/financial-critical,
the output feeds a downstream gate, or the input is adversarial, keep the
tier HIGH regardless of the table row matched — a cheap model that is subtly
wrong costs more than the tokens saved.

## Escalation ladder (zero-loss guarantee)

1. Execute at the routed tier.
2. Verify mechanically wherever possible (run the tests/build/lint; diff the
   output; check the schema).
3. On failure, low-confidence output, or a verification miss → re-run ONE
   tier up (ECONOMY → STANDARD → FRONTIER). Never retry the same tier twice.
4. FRONTIER failures are handled in-session (iterate, split, or council).

Net effect: worst case costs one cheap attempt extra; typical case saves the
frontier tokens entirely.

## Effort as a second axis

Model choice and `reasoning_effort` are independent levers. Set effort
explicitly on every dispatch. Never pay high/max effort for table rows 1–5,
even when a capable model is required for other reasons (e.g. long context).
Row 7's `max` is a FLOOR, not a target — the top row never drifts down under
cost pressure.

## Orchestrator-turn rules

- The main session stays on the user-selected model; do NOT delegate simple
  2–5-tool-call actions just to save tokens — delegation overhead can exceed
  the savings. Route only genuinely delegable units of work.
- In multi-agent workflows (swarms, pipelines), assign each stage its tier
  per the table — ECONOMY scouts feeding a FRONTIER synthesizer.
- Set the `model` parameter EXPLICITLY on every `task` dispatch above the
  agent type's default class — an omitted parameter silently inherits
  defaults; verify the default class matches the routed tier.
- Skill-pinned model choices override the table (e.g. `council` pins frontier
  members at max effort; `ms` pins Microsoft Learn verification flow).

## Delivery on this platform (Copilot CLI specifics) — v3.0

1. **Structural pins.** `settings.json` → `subagents.agents` pins each
   agent type's default model+effort (explore/task = ECONOMY low,
   code-review/research = STANDARD medium, general-purpose/security-review
   = inherit). Pins are DEFAULTS, not caps: omitting the `model` parameter
   on a `task` dispatch applies the pin; setting it explicitly routes UP
   for rows 6–7. Config cannot be "forgotten" mid-session — rows 1–3 are
   now deterministic without per-turn recall.
2. **Ambient rubric.** The compact routing table lives inline in
   `copilot-instructions.md` (injected every turn). This file is reference
   only — no per-batch re-reads (that rule measurably failed and itself
   cost input tokens).
3. **Runtime model resolution.** Resolve tier members from the model list
   visible in the current session's `task` tool definition, never from
   names memorized here.
4. **Audit trail.** Name the routed tier AND effort in the progress update
   when delegating (e.g. "row 2 → ECONOMY explore, low") — greppable
   compliance evidence consumed by the analyzer.
5. **Fail open.** Routing is a cost optimization, not a security gate — if
   classification is unclear, proceed on the default/session model.

## Self-improvement protocol (v3.0)

The deployment reviews its own efforts and results and tunes itself within
hard bounds. Components (all under `~\.copilot\routing\`):

- `analyze_routing.py` — deterministic, LLM-free analyzer over the local
  session store and event logs. KPIs: frontier cost share, avg main-session
  input tokens/turn, ECONOMY share of mechanical dispatches, subagent
  escalation rate. Appends snapshots to `state.json` (trend memory), writes
  `report-latest.md`, exit code 1 on breach.
- `targets.json` — KPI targets, tier name patterns, and `pin_bounds`
  (floor/ceiling per agent type). Targets change only by user decision.
- `CHANGELOG.md` — append-only log of every tuning action with evidence,
  before/after, revert condition, and VERIFIED/REVERTED status.
- `/route-tune` skill — the tuning agent, manually run: a cycle happens only
  when a human invokes it, never on a timer. Bounded self-modification: max
  one pin change (one tier step, within bounds) + one rubric wording
  refinement per cycle; never touches general-purpose/security-review pins,
  the row-7 floor, or the high-stakes override; verifies its previous
  change against the next cycle's KPIs and auto-reverts on regression
  (then 3-cycle cool-down on that change).
- A weekly scheduled analyzer run keeps the report fresh — a Task Scheduler
  task named `CopilotRoutingAnalyzer` on Windows, cron or a launchd agent on
  macOS/Linux. That job is LLM-free and read-only: it measures, it never tunes.

Feedback signals and their levers:
- escalation rate > 15% → pins too cheap → raise one class.
- escalation ≈ 0% for 2+ clean cycles → try one step cheaper (bounded).
- economy share of mechanical dispatches < 80% → rubric wording or skill
  mis-pins → refine wording, never loosen the pin.
- main input tokens/turn > 50K → context hygiene problem, not a routing
  problem → view_range discipline, delegate verbose output, suggest
  /clear /new /compact.
- frontier cost share > 50% driven by the MAIN role → user-only lever
  (session default model in `settings.json`); the tuner may only advise.

## Non-goals

- Never downgrade the tier of user-facing final answers/synthesis.
- Never route security-sensitive review below FRONTIER.
- Never spend tokens on a routing debate — the rubric is a lookup, not a
  deliberation. Classify, route, move on.
