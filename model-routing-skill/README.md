# model-routing — deterministic, self-improving model routing for GitHub Copilot CLI

Spend frontier tokens only where fidelity requires them. This package is a
complete routing deployment: structural sub-agent model/effort pins, a
verifiability-first 7-row routing table, a deterministic LLM-free KPI
analyzer, and the full v3.1 specification with its measured version lineage.

Published for the general public: the goal is to help anyone running an
agentic CLI save real money/quota on LLM tokens without losing output
quality — with every design rule traceable to a measurement (sound
provenance, documented below). Pairs with the companion
[**route-tune**](../route-tune-skill/) skill for the bounded, self-reverting
tuning loop.

Full documentation: [`docs/index.html`](docs/index.html) (GitHub Pages).

## Install

```sh
# macOS
./install.sh

# Windows (PowerShell 7+)
pwsh -File .\install.ps1        # add -WhatIf to preview
```

Installers run as the current user only, make no network calls, download
nothing, and **deliberately never edit** `settings.json` or
`copilot-instructions.md` — behavior-changing steps stay manual and are
printed at the end:

1. Pin your sub-agents in `~/.copilot/settings.json → subagents.agents`
   (explore/task = ECONOMY model, low effort; code-review/research =
   STANDARD model, medium effort).
2. Paste the compact routing table into `~/.copilot/copilot-instructions.md`
   so it is injected every turn.
3. Adjust `tier_patterns` in `~/.copilot/routing/targets.json` to your live
   model names.
4. Test: `python ~/.copilot/routing/analyze_routing.py`

## Prerequisites

- GitHub Copilot CLI with global custom instructions and
  `settings.json → subagents.agents` model/effort pins.
- Python 3.9+ (analyzer is standard-library only).
- The CLI's local session store under `~/.copilot/` (analyzer's only data
  source — nothing leaves the machine).
- A model list with at least two price classes so ECONOMY/STANDARD/FRONTIER
  patterns can resolve.
- Recommended: an OS scheduler (cron / launchd / Windows Scheduled Task) for a
  weekly KPI report refresh. The analyzer is the only piece worth automating —
  it measures, it never tunes.
- Optional: the companion route-tune skill for closed-loop tuning. It is
  manually run — a cycle happens only when you invoke `/route-tune`, never on
  a timer.

## Layout

| Path | Purpose |
|---|---|
| `routing/analyze_routing.py` | Deterministic, stdlib-only KPI analyzer (LLM-free) |
| `routing/targets.json` | KPI targets, cache weights, tier patterns, pin bounds |
| `instructions/model-routing.md` | Full v3.1 specification with version lineage and rationale |
| `install.ps1` / `install.sh` | Current-user, backup-first installers (Windows PS7 / macOS bash) |
| `docs/index.html` | GitHub Pages documentation |

## Method & cost discipline

Lowering token consumption is not a side effect of this package — it is the
entire point, and the design is built to make the saving real rather than
rhetorical. Routing decisions are made by *verifiability*, so work whose output
can be machine-checked (tests, builds, lint, schemas, exact diffs) or simply
extracted from files falls to a cheaper tier losslessly, while generative,
unverifiable judgment stays at the top. The pins are structural rather than
advisory because an earlier generation proved that prose guidance alone
produced measurable non-compliance. The analyzer that scores all of it runs
zero LLM calls and reads only local session data, so measuring the saving never
costs tokens of its own.

The routing table, tier semantics, KPI definitions, and pin bounds were
deliberated across an AI council spanning three independent vendors — each
answering independently before anonymized cross-review — precisely because a
routing rule that is subtly wrong costs more than the tokens it saves:

| Vendor | Frontier model |
|---|---|
| Anthropic | Claude Fable 5 |
| Google | Gemini 3.1 Pro |
| OpenAI | GPT-5.6 Sol |

That cross-vendor pass is also why the KPI denominators are ungameable: a
single-model design tends to grade its own homework, and the peer review is
what caught it. Claims here are grounded in primary vendor documentation and
published prior artifacts rather than model recall — the derivations follow, with
original engineering separated from adapted work.

No percentage of savings is claimed anywhere in this package. The mechanisms
are documented and the arithmetic is yours to run against your own KPIs, which
is exactly what `routing/analyze_routing.py` is for.

## Sources & derivation

- **Primary source — original iterative engineering:** v3.1 of a spec evolved
  across three generations on live Copilot CLI deployments (v1 hardcoded names
  → stale; v2 advisory prose → measured non-compliance; v3.0 structural pins +
  closed tuning loop; v3.1 cache-aware KPIs + ungameable denominators after a
  cross-machine peer review between two independent deployments). The lineage
  and forcing measurements are preserved in `instructions/model-routing.md`.
- **Platform:** [GitHub Copilot CLI documentation](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli)
  (custom skills, instructions, sub-agent configuration).
- **Related prior artifacts (context, not derivation):**
  [FrugalGPT (arXiv:2305.05176)](https://arxiv.org/abs/2305.05176) and
  [RouteLLM (arXiv:2406.18665)](https://arxiv.org/abs/2406.18665) route by
  learned difficulty prediction; this system routes by verifiability and
  dispatch surface so the self-tuning loop cannot game its own metrics.
