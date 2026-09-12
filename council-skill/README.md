# council — AI Council skill for GitHub Copilot CLI

Three fixed vendor seats (Anthropic, Google, OpenAI), each filled at run
time with the vendor's latest deep-reasoning flagship model, answer a
problem independently, anonymously peer-review each other's answers,
then iterate under a clerk orchestrator to strict all-member consensus
(every seat returns a valid APPROVE, max 2 fresh-context checks). Every run
ends in a verdict with preserved dissent and an explicit flip condition. No
model IDs are hard-coded — the roster resolves from the live model catalog
per run, so the skill needs no editing as catalogs evolve. Approval means
publication approval under the rubric, never established accuracy.

**Revision 1.2.0 (2026-09-12):** the specification was reviewed by a council
of the three vendors' current flagships and revised in thirteen places —
see [`CHANGELOG.md`](CHANGELOG.md). **1.2.2:** the review's one preserved
dissent (an enforced, not declared, tool-free profile for every seat) is
resolved in the reference implementation. **1.2.3:** the first
paired-evaluation pilot ran on nine labelled briefs — results, limits and
the two protocol fixes it forced are in [`EVALUATION.md`](EVALUATION.md);
no accuracy gain over a single grounded model was measurable on those
briefs.

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
- Access to the deep-reasoning flagship tier of Anthropic, Google, and
  OpenAI in the session's model list (seats resolve at run time; a vendor
  with no servable flagship aborts the run before Round 1, disclosed).
- Session-local private scratch storage for the alias↔identity map.
- An enforceable per-seat tool profile (agent tool allowlist, omitted tool
  definitions, or a permission rule) — the untrusted-content boundary is
  enforced by tools, not prose; fill in `references/harness-template.md`
  before the first run.

## Layout

| Path | Purpose |
|---|---|
| `skill/council/SKILL.md` | Roster, invariants, token discipline, 5-stage procedure, failure policy, acceptance tests |
| `skill/council/references/prompts.md` | Verbatim per-stage prompt templates |
| `skill/council/references/rubric.md` | Review dimensions, score anchors, gate arithmetic |
| `skill/council/references/output-template.md` | Fixed final-report structure and disclosures |
| `skill/council/references/harness-template.md` | Platform-neutral transport and tool-profile bindings to fill in before the first run |
| `CHANGELOG.md` | Dated change history, including the 2026-09-12 council self-review |
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

| Deliberation | Date | Anthropic | Google | OpenAI | Outcome |
|---|---|---|---|---|---|
| Original specification | August 2026 | Claude Fable 5 | Gemini 3.1 Pro | GPT-5.6 Sol | adopted with revisions |
| Self-review of this specification | 12 September 2026 | Claude Fable 5.1 | Gemini 3.1 Pro | GPT-6 Astra | REVISE; not unanimously approved after two checks (diagnostic agreement 93 / 96 / 88); thirteen changes adopted, dissent preserved in `CHANGELOG.md`; the preserved dissent resolved in the reference implementation the same day (1.2.2) |
| Shakedown of the revised protocol (reference implementation, closed-book statutory brief) | 12 September 2026 | Claude Fable 5.1 | Gemini 3.1 Pro | GPT-6 Astra | Unanimously approved after Check 2; Check 1 returned four FACT blockers on the clerk's draft, all corrected (90 / 100 / 90, then 95 / 100 / 99) |
| Paired-evaluation pilot 1 (nine briefs, four adversarial, arms S/C/P/K1/K2) | 12 September 2026 | Claude Fable 5.1 | Gemini 3.1 Pro | GPT-6 Astra | All arms correct on all briefs; 3 of 9 full runs unanimous; six correct answers blocked by two structural rules, both fixed in 1.2.3 — see `EVALUATION.md` |

Those rows are a dated record of who deliberated the spec, not a roster. The
skill itself pins no model: each row lists what the vendors' catalogs offered
on that date, and a council convened today would resolve its own seats from
the live catalog. The September review ran with a deep-research evidence
packet — the original llm-council source, current vendor documentation on
multi-agent orchestration, LLM-as-judge and deep research, and 25
peer-reviewed papers (all linked in `CHANGELOG.md`) — and each seat's own web research where its transport
allowed it; the review's own transport incidents (a seat losing web access, a
seat exhausting its output cap on reasoning, a lost conversation resume)
became changes C-8 and C-9.

Claims that could be grounded were grounded in primary documentation and
published prior artifacts rather than model recall — the derivations are listed
below, separated into adapted method and original extensions.

## Sources & derivation

- **Method:** Andrej Karpathy's [llm-council](https://github.com/karpathy/llm-council)
  (independent answers → anonymized cross-review → chairman synthesis) and
  [llmcouncil.ai](https://llmcouncil.ai).
- **Extensions original to this skill:** run-time roster resolution by
  capability (fixed vendors, no hard-coded model IDs, tier-conflict rule);
  frozen single-pushback intake brief; strict all-seats APPROVE gate with
  self-classified FACT / SAFETY / PREFERENCE blockers and a bounded 2-check
  fresh-context revision loop; clerk-never-judge invariant; source-faithfulness
  check on the clerk's draft; SOURCES / RECALL / EVIDENCE_GAP research
  contract; STATE_CAPSULE seat-state portability; mandatory untrusted-content
  boundary (UNTRUSTED_DATA fencing, tool-enforced member profiles, mechanical
  defanging of instruction-shaped text); per-stage token/tool budgets and
  run ceilings; audit manifest and score history; paired-evaluation fixture;
  degraded-run and failure-recovery policies.
- **Evidence behind the 2026-09-12 revision** — the complete linked list (23
  vendor pages, 25 packet papers, 8 seat-cited papers) is in
  [`CHANGELOG.md`](CHANGELOG.md#sources-consulted-for-the-2026-09-12-review);
  the load-bearing items:
  - Anthropic — [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents);
    [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system);
    [Mitigate jailbreaks and prompt injections](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks)
  - OpenAI — [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices);
    [Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create);
    [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state);
    [Deep research](https://developers.openai.com/api/docs/guides/deep-research);
    [Agent builder safety](https://developers.openai.com/api/docs/guides/agent-builder-safety)
  - Google — [Multi-agent patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/);
    [ADK workflow agents](https://adk.dev/agents/workflow-agents/);
    [Gemini models](https://ai.google.dev/gemini-api/docs/models);
    [I/O 2026 developer highlights](https://blog.google/innovation-and-ai/technology/developers-tools/google-io-2026-developer-highlights/)
  - Papers — Du et al. 2023, [multi-agent debate](https://arxiv.org/abs/2305.14325);
    Verga et al. 2024, [panel of LLM judges](https://arxiv.org/abs/2404.18796);
    Panickssery et al. 2024, [self-preference in LLM evaluators](https://arxiv.org/abs/2404.13076);
    Tripathi et al. 2025, [pairwise vs pointwise judging](https://arxiv.org/abs/2504.14716);
    Yao et al. 2025, [sycophancy in multi-agent debate](https://arxiv.org/abs/2509.23055);
    Li et al. 2025, [Self-MoA](https://arxiv.org/abs/2502.00674);
    Hirsch et al. 2026, [error origin in deep-research pipelines](https://arxiv.org/abs/2608.24306);
    Acharya et al. 2026, [robust panels of LLM judges](https://arxiv.org/abs/2606.30931);
    Kapetanović 2026, [anchoring bias in LLM-as-a-judge](https://arxiv.org/abs/2608.25869);
    Chen, Saha & Bansal 2023, [ReConcile](https://arxiv.org/abs/2309.13007).
