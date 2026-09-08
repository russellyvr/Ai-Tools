# Ai Tools

Skills and deployments for agentic command-line AI — built around one idea:
spend frontier-model tokens only where fidelity actually requires them, and
prove the rest with measurement rather than assertion.

Frontier models give you more deterministic results, but at a significant
cost. Past the initial analysis of a prompt, lower-cost models are perfectly
adept at finishing the task — at a significant saving. That is why I built
this, across two generations of frontier models. Ingest it, let your own model
work out what applies, and if it saves you precious tokens it has served its
purpose.

Each folder below is a standalone, self-contained entry. Nothing here depends
on anything outside its own directory except where noted, and every installable
package ships its own README, installers for macOS and Windows, and a full
documentation page under `docs/`. One entry — the cost-optimization playbook —
is a document rather than an installable package: it ships a README and the
playbook itself, and is read by a model rather than deployed.

Target platform for the installable packages: **GitHub Copilot CLI** (custom
skills in `~/.copilot/skills/`, global custom instructions, and
`settings.json → subagents.agents` model pins). The design ideas port to any
agentic CLI with per-dispatch model selection. The playbook entry is
platform-neutral — it is a document you hand to any model.

## Entries

| Entry | What it is | Start here |
|---|---|---|
| [`model-routing-skill/`](model-routing-skill/) | A deterministic, self-improving model-routing deployment: structural sub-agent model/effort pins, a verifiability-first 7-row routing table, and a standard-library-only KPI analyzer with no LLM in the measurement path. | [README](model-routing-skill/README.md) · [docs](model-routing-skill/docs/index.html) |
| [`route-tune-skill/`](route-tune-skill/) | The self-tuning half of the above: measures real routing KPIs, applies at most one bounded, logged, reversible change per cycle, verifies it next cycle, and reverts itself on regression. | [README](route-tune-skill/README.md) · [docs](route-tune-skill/docs/index.html) |
| [`council-skill/`](council-skill/) | A consensus-gated AI Council: three fixed vendor seats (Anthropic, Google, OpenAI), each filled at run time with that vendor's latest deep-reasoning flagship, answer independently, peer-review each other anonymously, and iterate to a strict all-seats verdict that preserves dissent and states its own flip condition. | [README](council-skill/README.md) · [docs](council-skill/docs/index.html) |
| [`evidence-ingest-skill/`](evidence-ingest-skill/) | A deterministic, LLM-free closed-corpus ingestion pipeline: folder in, locked RAG-ready corpus out, with a hash-chained legal chain of custody, default-deny network guard, fail-closed gates, and a 5-agent adversarial selftest. OCR via Google Document AI (audited exception) or a local loopback container. Installs for both GitHub Copilot CLI and Claude Code. | [README](evidence-ingest-skill/README.md) · [docs](evidence-ingest-skill/docs/index.html) |
| [`llm-cost-optimization-playbook/`](llm-cost-optimization-playbook/) | A portable brief you hand to any capable model — Claude, GPT, Gemini, local — so it profiles your own LLM spend and returns a ranked, costed optimization plan: intake, token profiling, free wins before tradeoffs, a prompt audit, and a mandated plan format. Distilled from Anthropic's published cost guidance and cited to it throughout. A document, not an installable package — there is no installer. | [README](llm-cost-optimization-playbook/README.md) · [playbook](llm-cost-optimization-playbook/PLAYBOOK.md) |

`model-routing-skill` and `route-tune-skill` are two halves of one system —
install model-routing first, since route-tune measures and tunes *that*
deployment. `llm-cost-optimization-playbook` is the reasoning those two
implement and installs nothing — start there if you want the why before the
how. `council-skill` and `evidence-ingest-skill` are each independent of the
rest.

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

| Vendor | Seat, as filled in August 2026 |
|---|---|
| Anthropic | Claude Fable 5 |
| Google | Gemini 3.1 Pro |
| OpenAI | GPT-5.6 Sol |

That table is a dated record of which models deliberated the designs, not a
current roster — those three were each vendor's deep-reasoning flagship at the
time, and the vendors have shipped newer ones since. Significant effort went
into that cross-vendor pass specifically because single-model design work reads
as confident whether or not it is correct.

**Sources over recall.** Every claim that could be grounded was grounded in
primary vendor documentation and published prior artifacts rather than model
memory. Each package lists its own derivations under "Sources & derivation" —
including which parts are original engineering and which are adapted, with
links to the upstream work.

No percentage of token savings is claimed anywhere in this repository as a
measured result of the work in it. Where figures do appear — as throughout the
cost-optimization playbook — they are quoted from published vendor
measurements, attributed to their source, and describe that vendor's workloads
rather than yours. The mechanisms here are documented; the arithmetic is yours
to run against your own KPIs, which is exactly what the analyzer is for.

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
