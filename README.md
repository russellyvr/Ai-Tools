# AI Tools

Skills and deployments for agentic command-line AI — built around one idea:
spend frontier-model tokens only where fidelity actually requires them, and
prove the rest with measurement rather than assertion.

Frontier models give you more deterministic results, but at a significant
cost. Past the initial analysis of a prompt, lower-cost models are perfectly
adept at finishing the task — at a significant saving. That is why I built
this, across two generations of frontier models. Ingest it, let your own model
work out what applies, and if it saves you precious tokens it has served its
purpose.

Each folder below is a standalone, self-contained package. Nothing here depends
on anything outside its own directory except where noted, and every package
ships its own README, installers for macOS and Windows, and a full
documentation page under `docs/`.

Target platform: **GitHub Copilot CLI** (custom skills in `~/.copilot/skills/`,
global custom instructions, and `settings.json → subagents.agents` model pins).
The design ideas port to any agentic CLI with per-dispatch model selection.

## Entries

| Entry | What it is | Start here |
|---|---|---|
| [`model-routing-skill/`](model-routing-skill/) | A deterministic, self-improving model-routing deployment: structural sub-agent model/effort pins, a verifiability-first 7-row routing table, and a standard-library-only KPI analyzer with no LLM in the measurement path. | [README](model-routing-skill/README.md) · [docs](model-routing-skill/docs/index.html) |
| [`route-tune-skill/`](route-tune-skill/) | The self-tuning half of the above: measures real routing KPIs, applies at most one bounded, logged, reversible change per cycle, verifies it next cycle, and reverts itself on regression. | [README](route-tune-skill/README.md) · [docs](route-tune-skill/docs/index.html) |
| [`council-skill/`](council-skill/) | A consensus-gated AI Council: three fixed frontier models answer independently, peer-review each other anonymously, and iterate to a strict all-seats verdict that preserves dissent and states its own flip condition. | [README](council-skill/README.md) · [docs](council-skill/docs/index.html) |

`model-routing-skill` and `route-tune-skill` are two halves of one system —
install model-routing first, since route-tune measures and tunes *that*
deployment. `council-skill` is independent of both.

## Method & cost discipline

Two things went into this work that are easy to skip and expensive to retrofit:
keeping token consumption down, and keeping the sources honest.

**Cost discipline is a design constraint here, not an afterthought.** Per-stage
output caps, batched sub-agent dispatch, prompt budgets, verifiability-first
routing, cache-aware KPIs, and audit manifests all exist for one reason — to
buy frontier-grade output at the lowest defensible token cost. In the routing
packages that constraint *is* the product; in the council package it is what
makes an otherwise extravagant method affordable enough to run.

**The designs were deliberated across an AI council spanning three independent
vendors**, not drafted by a single model. Each seat answered independently
before anonymized cross-review, so no one model's blind spot could quietly
become the specification:

| Vendor | Frontier model |
|---|---|
| Anthropic | Claude Fable 5 |
| Google | Gemini 3.1 Pro |
| OpenAI | GPT-5.6 Sol |

Significant effort went into that cross-vendor pass specifically because
single-model design work reads as confident whether or not it is correct.

**Sources over recall.** Every claim that could be grounded was grounded in
primary vendor documentation and published prior artifacts rather than model
memory. Each package lists its own derivations under "Sources & derivation" —
including which parts are original engineering and which are adapted, with
links to the upstream work.

No claim is made anywhere in this repository about a measured percentage of
token savings. The mechanisms are documented; the arithmetic is yours to run
against your own KPIs, which is exactly what the analyzer is for.

## Installing

Every package installs the same way, as the current user, with no network
calls and no sudo:

```sh
# macOS
./install.sh

# Windows (PowerShell 7+)
pwsh -File .\install.ps1        # add -WhatIf to preview
```

The installers are deliberately conservative: they copy documented text files,
back up anything they would overwrite, never touch `settings.json` or your
instructions file, and print the behavior-changing steps for you to apply by
hand. Read them before running them — they are short and commented.

## License

MIT. See [`LICENSE`](LICENSE).
