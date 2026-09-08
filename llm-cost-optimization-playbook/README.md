# LLM Cost Optimization Playbook

A single self-contained document you hand to a language model so it profiles
your own LLM spend and returns a ranked, costed optimization plan.

Read the playbook: [`PLAYBOOK.md`](PLAYBOOK.md).

## What it is

Anthropic has published a considerable amount of good guidance on reducing
Claude spend without losing quality — a blog post on the three main levers, a
cookbook with per-lever measured savings, a docs page separating free wins from
tradeoffs, and the `prompt-audit` and `cost-optimize` procedures inside the
`claude-api` skill. It is spread across four places, and none of it is in a
form you can simply hand to a model and get a plan back.

This is that consolidation: one file, everything inline, no browsing required.
Paste it into a conversation, describe what you run, and the model works
through the procedure and produces the plan.

## Who it is for

Anyone spending money on Claude — an API application, an agent loop, or an
agentic coding CLI — who wants the spend analyzed rather than guessed at.

The *subject* is Claude Platform cost. The *analyst* can be any capable model:
Claude, GPT, Gemini, or something local. The pricing table and cache multipliers
are Claude's; the method underneath is provider-neutral, and substituting
another provider's rates leaves the procedure intact.

## How to use it

**As a person.** Paste `PLAYBOOK.md` into a fresh conversation, then add one
line about what you run. The model asks for what it is missing and hands back
the plan.

**With an agent that has file or shell access** — Claude Code, Copilot CLI,
Codex, Cursor, an SDK loop. Paste it and tell the agent to measure first: it
should read your logs, config and prompt files directly rather than asking you
to transcribe numbers.

**As an instruction set.** The playbook addresses the reading model directly.
It defines the intake, the profiling formulas, the order levers must be applied
in, and the exact shape of the plan to emit. It is written to be followed, not
skimmed.

## What it covers

- Prime directives — cost per completed task, measure before changing, free
  wins before tradeoffs, model selection last, no tradeoff without an eval.
- Reference data — pricing, cache multipliers, the cache-duration decision
  table, and the break-even derivation.
- Intake and profiling, with the per-request cost formula and the five figures
  every plan must open with.
- Free wins in order: prompt caching, input hygiene, agent-loop efficiency,
  output control, batch processing.
- A prompt audit: the dated patterns that cost money on current models, and
  the keep list of things not to delete.
- Tradeoff levers: effort sweeps, model selection, advisor / orchestrator /
  decomposition architectures, and budgets.
- A validation protocol and a mandated output format for the plan.
- A closing section mapping every lever onto a local agentic CLI, where the
  static prefix, subagent model pins and cold starts are the equivalents.

## Sources & derivation

The method and every quantified figure in the playbook originate with
Anthropic. They are cited throughout and listed in the playbook's own Sources
section:

- [Reducing cost and improving performance with Claude Platform](https://claude.com/blog/reducing-cost-and-improving-performance-with-claude-platform)
  — the three levers, prompt anti-patterns, effort curves, benchmark results.
- [Cost Optimization on the Claude API](https://platform.claude.com/cookbook/cost-optimization-cost-optimization)
  — caching mechanics, per-lever measured savings, the model and effort sweep.
- [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)
  — free wins versus tradeoffs, the cache duration table, the decision tree.
- [`claude-api` skill](https://github.com/anthropics/skills/tree/main/skills/claude-api)
  — model IDs and pricing, and the `prompt-audit` and `cost-optimize`
  procedures reflected in the playbook's Steps 4 and 2.

What is added here rather than adapted:

- Consolidation of four sources into one portable file with nothing left
  behind a link, so a model with no browsing can still follow the whole
  procedure.
- A corrected cache break-even derivation. Treating the cache write as pure
  overhead gives 1.39 reads per write on a 5-minute cache, which is wrong —
  without caching you would have paid full price for that first call anyway.
  Solving `W + 0.1N = 1 + N` gives 0.28 reads per write at the 5-minute
  multiplier and 1.11 at the 1-hour. The playbook shows the derivation so it
  can be recomputed against any provider's multipliers.
- A mandated output format, so the plan comes back ranked by measured saving
  and split between changes that are safe to apply now and judgement calls
  that are not.
- The mapping of API-side levers onto a local agentic CLI install.

Every figure quoted describes the workload Anthropic measured, not yours. That
distinction is stated in the playbook and is the reason Step 2 exists.

## Before quoting any dollar figure

Verify the rates against
[Claude Platform pricing](https://platform.claude.com/docs/en/about-claude/pricing).
The table in the playbook was current as of mid-2026 and model pricing moves.

## License

MIT. See [`LICENSE`](../LICENSE) at the repository root.
