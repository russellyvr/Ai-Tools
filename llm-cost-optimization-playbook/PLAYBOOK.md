# LLM Cost Optimization Playbook

A self-contained brief you hand to any capable language model — Claude, GPT, Gemini, or a local model — so it can build you a costed, ranked optimization plan for your own LLM spend.

Everything the model needs is in this file. It does not need to browse the web, and it does not need access to your systems, though it will do a better job if you give it your usage numbers.

---

## How to use it

**If you are a person:** paste this entire file into a fresh conversation, then add one line describing what you run — "I have a customer support agent on Claude Sonnet, about 40,000 tickets a month" or "I use Claude Code all day and my bill doubled." The model will ask for what it is missing and hand back a plan.

**If you have an agent with file or shell access** (Claude Code, Codex, Cursor, an SDK loop): paste this file and tell it to measure first. It should read your logs, config, and prompt files directly rather than asking you to transcribe numbers.

**If you are the model reading this:** this file is your instruction set. Follow the procedure in order. Do not skip the intake. Do not recommend a model change before you have measured. Produce the plan format defined at the end.

---

## Prime directives

These override anything else in this file when they conflict.

1. **Optimize cost per completed task, not cost per token.** A more expensive model that finishes in one attempt is cheaper than a cheap one that fails and gets retried. Every recommendation must be priced per completed task, not per million tokens.

2. **Measure before you change anything.** A plan built without a token profile is guesswork. If you have no data, say so plainly in the plan and mark every estimate as unvalidated.

3. **Free wins before tradeoffs.** Caching, input hygiene, loop efficiency, output shaping, and batching cost nothing in quality. Effort reduction and model downgrades spend quality to buy savings. Never propose the second category before exhausting the first.

4. **Model selection is the last lever, not the first.** It is the most visible knob and the most damaging one to turn early. Architecture changes — decomposition, subagents, lazy loading — frequently beat a model downgrade and cost no accuracy.

5. **No tradeoff without an eval.** Free wins gate on cost measurement alone. Anything that could reduce quality requires a held-out test set before it ships. If the user has no eval, the first item in your plan is building one.

6. **One lever at a time.** Measure the baseline and the change together, keep or revert on evidence, and record the effect per change. Bundled changes cannot be attributed.

7. **A clean finding is a finding.** If caching is already working, say so and move on. An audit that invents problems to look thorough makes things worse.

---

## Reference data

### Claude model pricing

List rates per million tokens. These were current as of mid-2026 and **must be verified** against the provider's pricing page before dollar figures are quoted as fact. If the user is on another provider, substitute that provider's rates; the entire method below is provider-neutral.

| Model | ID | Context | Input | Output |
|---|---|---|---|---|
| Fable 5.1 | `claude-fable-5-1` | 1M | $10 / MTok | $50 / MTok |
| Opus 5 | `claude-opus-5` | 1M | $5 / MTok | $25 / MTok |
| Sonnet 5 | `claude-sonnet-5` | 1M | $2 / MTok | $10 / MTok |
| Haiku 4.5 | `claude-haiku-4-5` | 200K | $1 / MTok | $5 / MTok |

### Prompt cache multipliers

Relative to that model's input rate:

| Operation | Multiplier |
|---|---|
| Cache read | 0.1x |
| Cache write, 5-minute TTL | 1.25x |
| Cache write, 1-hour TTL | 2.0x |

### Break-even math, derived

A common error is to treat the cache write as pure overhead and conclude you need 1.39 reads per write to break even on a 5-minute cache. That is wrong: without caching you would have paid full price for that first call anyway.

Compare one write plus N subsequent reads of the same prefix:

```
cached   = W + 0.1N          (W = 1.25 for 5-minute, 2.0 for 1-hour)
uncached = 1 + N
break-even:  W + 0.1N = 1 + N   ->   N = (W - 1) / 0.9
```

- 5-minute TTL: N = 0.25 / 0.9 = **0.28 reads per write**
- 1-hour TTL: N = 1.0 / 0.9 = **1.11 reads per write**

In plain terms: on a 5-minute cache, caching pays for itself the moment a prefix is read back even once. On a 1-hour cache you need roughly one full re-read. Caching only loses money when prefixes are written and then almost never reused — which is a symptom of cache fragmentation, not a reason to disable caching.

Recompute this with the provider's actual multipliers if they differ.

### Cache duration decision table

| Situation | Setting |
|---|---|
| Turns seconds apart | 5-minute default |
| Roughly 1 turn in 20 resumes after a 5-minute to 1-hour gap | 1-hour TTL |
| Gaps commonly exceed 1 hour | 5-minute default; the 1-hour write premium will not be recovered |
| Long agent steps with minute-scale pauses | 5-minute TTL plus keep-alive requests to hold the cache warm |

---

## Step 1 — Intake

Ask for these. Ask for all of them at once, not one at a time. Accept "I don't know" and mark the resulting estimates as unvalidated rather than stalling.

**Scope**
- What is the workload? One-shot classification, multi-turn chat, an agent loop with tools, batch document processing, an interactive coding assistant?
- Which model and which effort/reasoning setting today?
- What volume — requests per day, and how bursty?
- Is latency user-facing, or can work wait?

**Money**
- Current spend per month, and per completed task if known.
- Where does the number come from: a provider usage report, application logs, or a guess?

**Quality**
- Is there an eval, a test suite, or any outcome check? How many cases?
- What is the quality bar — a pass rate, a human review threshold, a hard correctness requirement?
- What does a failure cost? A retried API call, or a wrong answer to a customer?

**Token profile** (the single most valuable input)
- Split per request: uncached input, cache reads, cache writes, output tokens.
- Current cache hit rate.
- Size of the static prefix: system prompt, tool definitions, any always-loaded instruction files.
- Number of distinct sessions or conversations, and the turn distribution — how many are one-shot.

**Surface**
- Can you share the system prompt and tool definitions? They are usually where the recoverable money is.
- Any always-loaded instruction files, skill or agent definitions, injected context, hooks that append text every turn?

If the user has an agent with file access, instruct it to gather all of the above directly instead of asking.

---

## Step 2 — Profile

Produce a token and cost profile before proposing anything.

Cost per request, with the multipliers above:

```
cost = ( uncached_input        * input_rate
       + cache_write_5m        * input_rate * 1.25
       + cache_write_1h        * input_rate * 2.00
       + cache_read            * input_rate * 0.10
       + output_tokens         * output_rate
       ) / 1_000_000
```

Then compute and state, in this order:

1. **Where the money is.** Rank the four buckets — uncached input, cache writes, cache reads, output — by share of spend. Every subsequent recommendation targets the largest bucket first.
2. **Cost per completed task**, including retries and failures. Not cost per call.
3. **The static prefix tax.** Size of everything re-sent on every call, multiplied by call count. Express it as *cost per 1,000 always-loaded tokens per month* so every proposed trim carries a price tag.
4. **Cold-start share.** What fraction of sessions are short enough that they pay a full cache write and never amortize it. This is the multiplier on the static prefix tax.
5. **The savings ceiling per lever.** Before recommending a lever, state the most it could possibly save given this profile. A lever whose ceiling is 2% of the bill does not belong near the top of the plan.

Ceilings overlap: caching a block and deleting that block are mutually exclusive savings on the same tokens. Deflate for overlap rather than adding ceilings together.

---

## Step 3 — Free wins, in order

Apply in this sequence. Each entry gives the mechanism, how to detect the opportunity, and published evidence of the magnitude. Cite the magnitude as evidence from a published case, never as a promise about the user's workload.

### 3.1 Prompt caching

**Mechanism.** The model's processed state for a prompt prefix is stored and read back instead of recomputed, at 10% of input price. Requires a byte-exact match on the full prefix, and the cache is per-model.

**Detect.** Cache hit rate below roughly 80% on a repetitive workload. Ordering that puts anything variable ahead of anything stable.

**Do.**
- Order the request static-first: system prompt, then tool definitions, then stable reference material, then the volatile conversation. Anything variable above stable content invalidates everything below it.
- Place explicit cache breakpoints between layers that change at different rates — a policy manual that changes monthly gets its own breakpoint ahead of per-request context.
- Never interpolate timestamps, request IDs, session counters, or "today's date" into the system prompt. This is the single most common cache killer.
- Apply system-prompt updates as a mid-conversation message rather than editing the cached prefix.
- Keep tool definitions stable and in a fixed order.
- Pre-warm the cache with a zero-output request when a burst is predictable.
- Raise to the 1-hour TTL only when the gap pattern justifies it per the decision table above.

**Evidence.** Published cookbook measurements: auto-caching alone cut a two-question workload 32%; correct breakpoint ordering — stable manual first, volatile intake second — saved 54% against the reverse order; caching cuts agent-loop cost by roughly 2.5x to 3.7x. On an insurance-claims agent, caching alone took cost per task from $0.2906 to $0.1498, a 48% reduction with no quality change.

**When not to.** Prefixes that are genuinely unique per request. Cache them and you pay the write premium for nothing.

### 3.2 Input hygiene — stop sending what the model can fetch

**Mechanism.** Large reference material sitting in the static prefix is paid for on every call whether or not the task needed it. Behind a tool, it is paid for only when read.

**Detect.** A system prompt over a few thousand tokens. Reference tables, policy documents, schemas, or data pasted inline. Long tool rosters where most tools are rarely called. Full-resolution images. Large CSV or JSON payloads pasted into context.

**Do.**
- Move bulky reference material behind a retrieval tool. A published case removed 10,945 tokens from a static prefix this way.
- Delete prose recaps of tools from the system prompt — the tool schemas already render into the request. Worth roughly 400 tokens in the same case.
- Defer rarely-used tool definitions so only a search tool plus the critical few load upfront. Published saving: ~429 tokens on a small roster, and up to **45% on a 500-tool roster**.
- Downscale images to the smallest resolution that preserves the task. 2048x1536 at 4,088 tokens versus 960x720 at 928 tokens is a **77% saving** with no measured performance loss.
- Push large data files through a code-execution sandbox instead of pasting them. A 5,000-row ledger cost 135,201 tokens ($0.6824) pasted versus 19,764 tokens ($0.1436) via the Files API — a **79% saving**, reported elsewhere as up to 92% on data queries.

**When not to.** If a document is needed on nearly every call, a tool round-trip costs more than caching it. Measure the hit rate first.

### 3.3 Agent-loop efficiency

**Mechanism.** In a multi-turn loop, every tool result stays in context and is re-sent on every subsequent turn. Cost grows quadratically with turn count unless bounded.

**Detect.** Agent conversations whose input token count climbs steadily across turns. Large tool results — file dumps, query results, page fetches — retained long after they were used.

**Do.**
- **Automated context editing:** clear old tool results past a token threshold, keeping the most recent few. Published saving: 12% on a three-task queue.
- **Server-side compaction:** summarize older turns rather than dropping them. Published saving: 16%, with history preserved.
- **Jagged pruning:** replace bulky tool results with one-line extracts, but only at task boundaries — pruning every turn invalidates the cache every turn and costs more than it saves. Published saving: 29%, and it beats naive pruning precisely because it respects the cache.
- **Subagents:** spin bulky subtasks off to a cheaper model that absorbs the intermediate results locally and returns a short extract. The orchestrator never sees the raw payload. Published saving: **78%** ($1.7945 to $0.3978 per task), and roughly 50% on any work larger than a single context window.

**When not to.** Aggressive pruning on tasks that need long-range recall will cause silent quality loss. Prune at boundaries, and eval it.

### 3.4 Output control

**Mechanism.** Output tokens cost five times input. A model asked for a memo writes a memo.

**Detect.** Long free-form responses where a structured answer would do. `max_tokens` used as a shaping tool rather than a backstop. Reasoning-heavy configurations on tasks that do not need reasoning.

**Do.**
- Specify the exact output shape with an example. Published saving: an open-ended memo at 4,096 output tokens ($0.1585) versus a structured one-liner at 61 tokens ($0.0580) — **63%**, at identical `max_tokens`.
- Even trivial format tightening pays: one-line versus two-line answer format measured **14%**.
- Use stop sequences so the model can halt early on inputs it cannot process. Published: 2,890 output tokens versus 13 when a sentinel triggered — **56%** on malformed input.
- Keep `max_tokens` high as a safety backstop, not a shaping mechanism. Truncated output that has to be regenerated is more expensive than a longer answer. If you see `stop_reason: max_tokens`, raise it.
- Watch reasoning tokens specifically: one benchmark's thinking tokens fell from 102,779 to 8,284 under optimization while accuracy held.

### 3.5 Batch processing

**Mechanism.** Non-interactive work submitted asynchronously, returned within 24 hours, at **50% off all tokens**. Stacks with caching.

**Detect.** Any workload where no human is waiting: nightly classification, backfills, evals, report generation, bulk extraction.

**Do.** Move it to the batch endpoint. Published: $0.7379 to $0.3653 on ten identical triage requests.

**When not to.** Anything interactive, and anything with a mid-loop tool call that needs a synchronous response.

---

## Step 4 — Audit the prompt itself

Prompts accumulate instructions written to work around failures in models that no longer exist. On current frontier models those instructions actively cost money and accuracy. A published audit of this kind on a customer-support prompt during a model upgrade cut cost **14.6%** while *raising* accuracy **5.3%**.

The discipline: every finding must name a specific pattern and a specific reason tied to current model behavior. Length alone is not a finding. An audit that deletes indiscriminately is worse than no audit.

### 4.1 Dated prompt text

- **Pressure language.** Caps-lock emphasis — MUST, CRITICAL, NEVER, ALWAYS, MANDATORY, "be maximally thorough" — over-triggers current models. Measured effects include unnecessary tool calls and redundant knowledge-base searches. Restate plainly, with the reason instead of the volume.
- **Verification rituals.** "Double-check your work", "re-read the file before answering", mandatory self-audit passes. These duplicate reasoning and tool calls on models that already verify internally.
- **Superseded scaffolds.** `<scratchpad>` tags, "think step by step", assistant-turn prefill to force JSON, inline lookup tables, word-count caps. Each has a native replacement now: reasoning configuration, structured outputs, or code.
- **Over-specification.** Numbered step choreography, long prohibition lists, a single gold example, bullet walls. Describe the goal, not the method.
- **Fossils.** Workarounds naming a retired model version, "no longer do X" phrasing, patch accretion, rules nothing enforces, identity stubs.
- **Output choreography.** Interim-update cadences and numeric ceilings ("at most N words") should be removed together and re-expressed as outcome framing.

### 4.2 Tool definitions

- **Under-described tools** need *more* text, not less: the contract, the mechanics, when *not* to use it, parameter semantics. Tool description detail usually grows during a good audit.
- **Over-steered tools** carry behavioral boosters that belong nowhere. Dial back to plain language.
- **Misplaced content** — worked examples, cross-references scolding the model, behavior smuggled into a description — moves out to documentation.
- **Duplication** — tool names restated in the system prompt, near-identical overlapping tools — gets deleted.
- Routing and trigger text is the exception: it may legitimately carry urgency, because under-triggering is the common failure there.

### 4.3 Configuration and architecture

- Deprecated parameters still being sent.
- Cache-hostile ordering (see 3.1).
- Budget countdowns or remaining-token counters surfaced to the model.
- The model executing a deterministic plan that belongs in code.
- Redundant subagents.
- No token accounting anywhere in the system.

### 4.4 The keep list — do not delete these

1. **Context is never cruft.** Audience, product, environment, quality bar, and the reasons behind rules all stay.
2. **Cruft is not length.** Harm comes from specific outdated instructions, not from word count.
3. **Fragile operations keep their exact scripts.**
4. **Tool contracts stay and often grow.**
5. **Prohibitions against demonstrated, current failures stay.** Only style-policing with no provenance goes.
6. **Format-pinning examples stay** where output format is genuinely load-bearing.
7. **Working redundancy that causes no errors stays.**

For each candidate line, ask: which failure, on which model, did this prevent — and does that model still run this workload? If nobody can answer, it is a removal candidate. If the answer is "current model, last month", it stays.

### 4.5 Verification

Probe behavior before and after with an eval or a minimal test — never by asking the model whether it needs an instruction. Change one item at a time where stakes are high. If a cut regresses, restore it in the simplest form that works. Re-audit at every model release.

---

## Step 5 — Tradeoff levers

Only after Steps 3 and 4, and only with an eval in place.

### 5.1 Effort and reasoning budget

Sweep effort across the range *before* touching model selection. Published curves:

- Hardest-tier coding tasks: low effort 11.5% accuracy at $5.35 per task; maximum effort 30.9% at $19.00. Roughly 2.7x the score for 3.5x the cost — worth it only if failures are expensive.
- Hard knowledge questions: low effort ~53% at ~$0.30; maximum ~61% at ~$2.23. The final step bought +0.5 points for 46% more cost, inside noise.
- General knowledge work: 13% to 31% savings at low effort with minimal quality loss.

Read the shape of the curve, not a single point. A flat curve means effort is buying nothing on that task and should be dropped. A steep curve means the task is genuinely hard and effort is the wrong place to economize.

**The strongest single move here:** where outcomes are machine-checkable, run everything at low effort and re-run only the failures at high. Published result: **91.7% pass rate for about half the cost** of running at default throughout.

### 5.2 Model selection

Rules:

- **Test a stronger model at lower effort before raising effort on a weaker one.** A published comparison found the newer frontier model at low effort matching the previous generation at high effort for roughly a third of the cost.
- **Upgrading is often a cost reduction.** Newer models typically land between 40% cheaper and 20% more expensive *per solved task*, because they solve more per attempt. Never assume newer means pricier.
- **Never pay a premium tier for the same effort range as a cheaper one.** If two models sit in the same capability band and one costs double, the expensive one needs a measured reason to exist in your stack.
- **A model at the same price as its successor is strictly dominated.** Move.
- **Price on your workload's tail, not its median.** The hard 10% is where cheap models fail and retries eat the savings.
- **Step down one tier at a time**, with the eval running.

Published sweep on a 10-case eval with a 10/10 quality bar:

| Configuration | Pass | Cost / task |
|---|---|---|
| Top tier, high effort, no cache | 10/10 | $0.2906 |
| Top tier, high effort, cached | 10/10 | $0.1498 |
| Top tier, low effort, cached | 10/10 | $0.1206 |
| **Mid tier, medium effort, cached** | **10/10** | **$0.0497** |
| Mid tier, low effort, cached | 8-9/10 | $0.0502 |
| Cheapest tier, cached | 4-7/10 | $0.0195 |

Note what that table shows: the mid tier at medium effort held the full quality bar at 17% of the baseline cost, and the cheapest tier failed it outright while the *low-effort mid tier* cost the same as medium and scored worse. The cheapest configuration that clears the bar is rarely the cheapest configuration.

### 5.3 Multi-model architectures

- **Advisor pattern.** A cheaper executor escalates hard cases to a frontier model. Published: +3.5 points on coding over a single model. Works only with a cheap upfront signal to gate the consult — a confidence band, a risk score, a value threshold. Without a gate, the executor makes wrong calls unilaterally and never escalates.
- **Orchestrator pattern.** A frontier model coordinates and delegates bulk work to cheaper workers. Roughly **50% savings** on work exceeding one context window.
- **Decomposition.** Split a task into narrow subtasks, each on a cheap model, with one capable model deciding against a rule card. Published: **93% cost reduction** ($0.2906 to $0.019 per task) at 9/10 accuracy. The caveat is serious — flattening a reference manual into a rule card loses its carve-outs and produces *systematic* misses rather than random ones. High leverage, high risk; needs the strongest eval of anything in this document.

### 5.4 Budgets

Set per-task and per-session token budgets from the 90th percentile of observed usage, not from the median. Tighten cautiously. Budgets are a runaway-loop backstop, not a cost lever — a task killed at its budget has consumed its tokens and delivered nothing.

---

## Step 6 — Validate

- Measure baseline and post-change in the same session, under the same conditions.
- For caching changes, discard the first request and measure from the second — otherwise you are measuring a cold write.
- Repeat until the signal clears the noise. Single-run deltas under about 5% are usually noise.
- Split your eval into train and test. Optimize against train; report against held-out test. Optimizations tuned on the full set overfit to it — a published hillclimbing run reported 90.5% on held-out data versus a 78.6% baseline precisely because it kept the split honest.
- A minimum viable eval is 20 to 30 frozen cases, one judgment method, and one cost estimate. That is enough to gate a tradeoff. It is not enough to prove a subtle regression.
- Shadow-run the winning configuration against production traffic before cutting over, then confirm the saving in the provider's usage report afterwards. Projected savings and billed savings differ more often than anyone expects.

---

## Step 7 — Deliver the plan

Output in exactly this shape.

**1. Profile.** Where the money goes today: token split by bucket, cost per completed task, static prefix tax per 1,000 tokens per month, cold-start share. State the data source for each figure and mark anything estimated.

**2. Ranked findings.** Largest measured saving first. Each finding gets:

| Field | Content |
|---|---|
| Finding | One sentence |
| Evidence | The number in the user's own data that supports it |
| Ceiling | The most this lever could save, given their profile |
| Lever | The specific change |
| Class | Free win / Tradeoff |
| Risk | What could get worse, and how it would show up |
| Gate | What must be true before shipping — nothing, or a named eval |

**3. Split the plan in two.** Configuration changes that are safe to apply immediately, and judgement calls that require deciding what to give up. Never blur these together. The first list can be executed today; the second needs a human who understands the domain.

**4. Skipped levers, with reasons.** A lever that does not apply is worth one line each. It stops the user asking about it later.

**5. Sequence.** The order to apply changes, one at a time, with what to measure after each.

**6. Clean checks.** What you examined and found healthy. This is not filler — it tells the user where *not* to spend effort.

If the honest answer is "no changes recommended", say that. A well-configured system is a valid result.

---

## Adapting this to a local coding agent or CLI

The same levers apply, with different names for the same things. If the user runs an agentic coding tool rather than an API application:

- **The static prefix** is their always-loaded instruction file plus every tool, skill, agent, and command description injected at session start. It is re-read on every single API call in every session. Price it per 1,000 tokens per month and it usually reframes the whole conversation.
- **Subagent model pins** are the equivalent of model selection. A subagent definition with no explicit model inherits whatever the parent session runs — so a mechanical, verifiable task like reformatting or re-fetching a citation can silently execute on the most expensive tier available. Every delegated role should carry an explicit model appropriate to its verifiability.
- **Route by verifiability, not by intuition.** Work whose output is machine-checkable — tests, builds, lint, schema validation, exact-match extraction — downgrades to a cheap tier losslessly. Generative work under ambiguity, adversarial input, and anything irreversible stays on the strongest tier. Effort is a second, independent dial: do not pay high effort for mechanical work.
- **Cold starts** are the multiplier. Sessions that run one or two turns pay a full cache write of the entire prefix and never amortize it. If half the sessions are one-shot, every token trimmed from the prefix pays back twice.
- **Listing budgets and tool rosters** are the local version of `defer_loading`. If every available capability's description is injected into every session, most of that text is being paid for and never read.
- **Delegation is context isolation, not cheap thinking.** Hand work to a subagent when it would otherwise flood the main context with output. Delegating a two-call task to save tokens costs more than it saves.

---

## Sources

- Anthropic, [Reducing cost and improving performance with Claude Platform](https://claude.com/blog/reducing-cost-and-improving-performance-with-claude-platform) — the three levers, prompt anti-patterns, effort curves, benchmark results.
- Anthropic, [Cost Optimization on the Claude API](https://platform.claude.com/cookbook/cost-optimization-cost-optimization) — the cookbook; caching mechanics, per-lever measured savings, the model and effort sweep.
- Anthropic, [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) — free wins versus tradeoffs, cache duration table, decision tree.
- Anthropic, [`claude-api` skill](https://github.com/anthropics/skills/tree/main/skills/claude-api) — model IDs and pricing, and the `prompt-audit` and `cost-optimize` procedures reflected in Steps 4 and 2.
- Pricing: [Claude Platform pricing](https://platform.claude.com/docs/en/about-claude/pricing). Verify before quoting.

All figures quoted in this playbook come from those published sources and describe the workloads measured there. They indicate the magnitude a lever can reach. They are not predictions about your system — that is what Step 2 is for.
