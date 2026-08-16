# council — AI Council skill for GitHub Copilot CLI

Three fixed frontier models (Claude Fable 5, Gemini 3.1 Pro, GPT-5.6 Sol)
answer a problem independently, anonymously peer-review each other's answers,
then iterate under a clerk orchestrator to strict all-member consensus
(every seat >= 90/100, max 2 revision checks). Every run ends in a verdict
with preserved dissent and an explicit flip condition.

Full documentation: [`docs/index.html`](docs/index.html) (GitHub Pages).

Published for the general public: multi-model deliberation is expensive by
design, so the skill's token-discipline rules (per-stage output caps, batched
launches, prompt budgets, audit manifests) exist to give you frontier-grade,
dissent-preserving answers at the lowest defensible cost — with the method's
provenance documented below.

## Install

```sh
# macOS
./install.sh

# Windows (PowerShell 7+)
pwsh -File .\install.ps1        # add -WhatIf to preview
```

Installers run as the current user only, make no network calls, download
nothing, and never touch your configuration — they copy the skill folder,
backup-first, and print next steps. Manual equivalent:

```sh
cp -r skill/council ~/.copilot/skills/council
# restart the Copilot CLI session, then:
/council <your question or decision>
```

## Prerequisites

- GitHub Copilot CLI with custom-skill support (`~/.copilot/skills/`).
- Sub-agent (`task`) tool with per-dispatch `model` + `reasoning_effort`
  selection, blocking reads, and follow-up messaging.
- Access to at least three heterogeneous frontier models (edit the roster
  in `SKILL.md` if your model list differs).
- Session-local private scratch storage for the alias↔identity map.

## Layout

| Path | Purpose |
|---|---|
| `skill/council/SKILL.md` | Roster, invariants, token discipline, 5-stage procedure, failure policy, acceptance tests |
| `skill/council/references/prompts.md` | Verbatim per-stage prompt templates |
| `skill/council/references/rubric.md` | Review dimensions, score anchors, gate arithmetic |
| `skill/council/references/output-template.md` | Fixed final-report structure and disclosures |
| `install.ps1` / `install.sh` | Current-user, backup-first installers (Windows PS7 / macOS bash) |
| `docs/index.html` | GitHub Pages documentation |

## Method & cost discipline

Multi-model deliberation is expensive by construction — three frontier seats,
a cross-review round, and a bounded revision loop. Sustained effort therefore
went into making it affordable enough to actually run: per-stage output caps,
batched sub-agent launches, explicit prompt budgets, a clerk that orchestrates
without ever judging, and an audit manifest that makes every token spent
attributable after the fact. The token discipline in `SKILL.md` is a
first-class part of the design, not housekeeping bolted on afterwards.

The skill's own specification, rubric, and stage prompts were themselves
deliberated across an AI council spanning three independent vendors — each
seat answering independently before anonymized cross-review, so that no single
model's blind spot could quietly become the spec:

| Vendor | Frontier model |
|---|---|
| Anthropic | Claude Fable 5 |
| Google | Gemini 3.1 Pro |
| OpenAI | GPT-5.6 Sol |

Claims that could be grounded were grounded in primary documentation and
published prior artifacts rather than model recall — the derivations are listed
below, separated into adapted method and original extensions.

## Sources & derivation

- **Method:** Andrej Karpathy's [llm-council](https://github.com/karpathy/llm-council)
  (independent answers → anonymized cross-review → chairman synthesis) and
  [llmcouncil.ai](https://llmcouncil.ai).
- **Extensions original to this skill:** frozen single-pushback intake brief;
  strict all-seats-≥90 consensus gate with bounded 2-check revision loop;
  clerk-never-judge invariant; STATE_CAPSULE seat-state portability;
  EVIDENCE_GAP governance; per-stage token/tool budgets; audit manifest;
  degraded-run and failure-recovery policies.
