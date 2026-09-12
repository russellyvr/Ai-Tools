# Changelog — council-skill

## 1.2.2 — 2026-09-12 — the preserved dissent is resolved in the reference implementation

The OpenAI seat's unresolved blocker from the 1.2.0 review (R1: a
"packet-only" profile declared in prose is not enforcement) is closed in
the author's reference implementation. The Google seat's CLI transport was
measured and found unable to enforce a tool-free profile in headless mode
(57 tools exposed, including shell and file writes; its sandbox and plan
flags do not stop them), so under this skill's own failure policy that
seat was unfillable for closed-book stages. The seat now runs on the
vendor's API, where the request body carries no tool definitions on
closed-book stages and only the vendor's search tool on research briefs —
enforcement by request body, as R1 asked. The specification text in this
package already required exactly that; the change is recorded here so the
dissent's disposition is not lost. Housekeeping in the same pass: the
auth gate no longer types a model id anywhere.

## 1.2.0 — 2026-09-12 — the council reviews its own specification

On 12 September 2026 this skill's specification was put before a council of
the three vendors' current flagships — **Claude Fable 5.1** (Anthropic),
**Gemini 3.1 Pro** (Google), **GPT-6 Astra** (OpenAI) — with a
deep-research evidence packet: the original Karpathy llm-council source,
current Anthropic / OpenAI / Google documentation on multi-agent
orchestration, LLM-as-judge and deep research, and 25 peer-reviewed papers
on multi-agent debate, ensembles, judge bias and refinement loops (all
listed under *Sources consulted* below, with the further papers the seats
themselves cited and the orchestrator verified). The
verdict was **REVISE**, not unanimously approved after two checks
(diagnostic agreement 93 / 96 / 88). The main dissent, from the OpenAI seat,
is preserved: unanimity is a defensible publication policy but not a
demonstrated accuracy mechanism, and a "packet-only" profile declared in
prose is not enforcement. Everything below is what the council changed;
each marker appears in the files where the change landed.

- **C-1 — Untrusted-content boundary enforced by tool profile, not prose.**
  Every relayed block is fenced; enforcement per transport is written down
  in `references/harness-template.md`; a transport that cannot enforce the
  profile makes the seat unfillable for that mode; a controlled
  citation-verification fetch is the one permitted exception.
- **C-2 — Source-faithfulness check on the clerk's draft before Stage 4.**
  The claim ledger carries a source passage per claim; unverifiable claims
  are removed or relabelled; a decision-critical assumption makes the
  verdict conditional.
- **C-3 — Sourced research as a first-class Round-1 mode.** SOURCES and
  RECALL labels, EVIDENCE_GAP, a bounded multi-step research allowance for
  research briefs, per-seat attestation of whether research tools worked;
  vendor deep-research products are never seated.
- **C-4 — Capability-based eligibility.** Product-name tiers ("Flash",
  "Sonnet") are no longer excluded by name; distilled tiers still are. A
  `tier_conflict` is recorded when a newer non-flagship generation outranks
  the newest flagship, and resolved by a stated rule with disclosure.
- **C-5 — Fresh-context, score-blind consensus checks with a categorical
  gate.** Checks go to fresh agents carrying the brief, the draft, the
  evidence and an anonymous objection ledger — never the seat's own prior
  answer, capsule or score. Verdicts are APPROVE / REVISE / ABSTAIN with
  claim-linked blockers self-labelled FACT / SAFETY / PREFERENCE; unanimity
  is kept as a chosen publication policy; the 0-100 score becomes a
  diagnostic. New status: "Approved by two seats; preference dissent
  preserved".
- **C-6 — Two-check cap kept as budget policy;** Check 2 runs only after a
  material change in text or evidence.
- **C-7 — Peer review:** deterministic counterbalanced ordering; ranking
  optional; the same-model note now says masking cannot remove
  self-recognition.
- **C-8 — Budget semantics that match what is billed:** 9-12 planned seat
  requests within 21 + 2; the hard cap of 7 now includes formatting
  repairs; run-level token, time and spend ceilings; a reply cut off by an
  output cap that includes reasoning tokens is a cap breach.
- **C-9 — Harness observability:** executed model ID verified per reply;
  probe IDs read from the catalog; continuity loss treated as rehydration;
  per-seat tool inventory recorded.
- **C-10 — Audit manifest extended;** cross-run score history; new status
  "Aborted after Round 1: fewer than two seats".
- **C-11 — Paired evaluation fixture** required before any accuracy claim;
  every report states that approval is publication approval under the
  rubric, not established accuracy.
- **C-12 — "When NOT to convene"** adds verifiable or tool-checkable
  questions.
- **C-13 — Housekeeping:** `REQUIRED_CHANGES_TO_REACH_90` renamed
  `REQUIRED_CHANGES`.

Not adopted from the review, and recorded here so the dissent is not lost:
the OpenAI seat's request that any prose-declared "packet-only" profile be
treated as an outright protocol failure rather than a disclosed downscale.
The skill now makes such a seat unfillable for research mode and requires
an enforced tool-free profile for closed-book stages; where a platform
cannot provide one, the report says so. (Resolved in the reference
implementation on the same day — see 1.2.2 above.)

### Sources consulted for the 2026-09-12 review

Everything below is public. Vendor pages were fetched on 2026-09-12; every
paper was resolved by identifier on Semantic Scholar the same day. The
evidence packet itself and the run transcripts are not published.

**Original provenance**

- Andrej Karpathy, llm-council — https://github.com/karpathy/llm-council
  (README, `backend/council.py`, `backend/config.py`)
- llmcouncil.ai — https://llmcouncil.ai

**Vendor documentation**

- Anthropic, "Building effective agents" — https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "How we built our multi-agent research system" — https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, "Mitigate jailbreaks and prompt injections" — https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- Anthropic, Claude Code subagents — https://code.claude.com/docs/en/sub-agents
- Anthropic, Claude models overview — https://platform.claude.com/docs/en/about-claude/models/overview
- OpenAI, Reasoning best practices — https://developers.openai.com/api/docs/guides/reasoning
- OpenAI, Evaluation best practices — https://developers.openai.com/api/docs/guides/evaluation-best-practices
- OpenAI, Conversation state — https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI, Background mode — https://developers.openai.com/api/docs/guides/background
- OpenAI, Deep research — https://developers.openai.com/api/docs/guides/deep-research
- OpenAI, Agent builder safety — https://developers.openai.com/api/docs/guides/agent-builder-safety
- OpenAI, Responses API reference (create) — https://developers.openai.com/api/reference/cli/resources/responses/methods/create
- OpenAI, Models — https://developers.openai.com/api/docs/models
- OpenAI Agents SDK, Orchestrating multiple agents — https://openai.github.io/openai-agents-python/multi_agent/
- Google, Gemini API thinking — https://ai.google.dev/gemini-api/docs/thinking
- Google, Gemini Deep Research agent — https://ai.google.dev/gemini-api/docs/deep-research
- Google, Gemini models — https://ai.google.dev/gemini-api/docs/models
- Google, Gemini 3.8 Flash announcement — https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/
- Google, I/O 2026 developer highlights — https://blog.google/innovation-and-ai/technology/developers-tools/google-io-2026-developer-highlights/
- Google ADK, Workflow agents — https://adk.dev/agents/workflow-agents/
- Google, "A developer's guide to multi-agent patterns in ADK" — https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- Antigravity CLI, Headless mode — https://antigravity.google/docs/cli/headless/
- Artificial Analysis, Gemini 3.8 Flash vs Gemini 3.1 Pro — https://artificialanalysis.ai/models/comparisons/gemini-3-8-flash-vs-gemini-3-1-pro-preview

**Peer-reviewed and preprint literature in the evidence packet (25)**

Multi-agent debate
- Du et al. 2023, "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (ICML 2024) — https://arxiv.org/abs/2305.14325
- Liang et al. 2023, "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate" — https://arxiv.org/abs/2305.19118
- Zhou & Chen 2025, "Adaptive heterogeneous multi-agent debate for enhanced educational and factual reasoning in large language models" — https://doi.org/10.1007/s44443-025-00353-3
- Smit et al. 2023, "Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs" (ICML 2024) — https://arxiv.org/abs/2311.17371
- Yao et al. 2025, "Peacemaker or Troublemaker: How Sycophancy Shapes Multi-Agent Debate" — https://arxiv.org/abs/2509.23055
- Hao et al. 2026, "Not All Flips Are Conformity: Decomposing Stance Convergence in Multi-Agent LLM Debate" — https://arxiv.org/abs/2606.00820

Ensembles and heterogeneity
- Wang et al. 2024, "Mixture-of-Agents Enhances Large Language Model Capabilities" — https://arxiv.org/abs/2406.04692
- Li et al. 2025, "Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?" — https://arxiv.org/abs/2502.00674
- Chen 2026, "When Does Combining Language Models Help? A Co-Failure Ceiling on Routing, Voting, and Mixture-of-Agents Across 67 Frontier Models" — https://arxiv.org/abs/2606.27288
- Ali 2026, "Quantifying Diversity of Thought: A Predictive Law of Weighted LLM Ensemble Lift" — https://arxiv.org/abs/2607.17384

LLM-as-judge bias and scoring
- Zheng et al. 2023, "Judging LLM-as-a-judge with MT-Bench and Chatbot Arena" — https://arxiv.org/abs/2306.05685
- Panickssery et al. 2024, "LLM Evaluators Recognize and Favor Their Own Generations" — https://arxiv.org/abs/2404.13076
- Koo et al. 2023, "Benchmarking Cognitive Biases in Large Language Models as Evaluators" — https://arxiv.org/abs/2309.17012
- Li et al. 2023, "PRD: Peer Rank and Discussion Improve Large Language Model based Evaluations" — https://arxiv.org/abs/2307.02762
- Tripathi et al. 2025, "Pairwise or Pointwise? Evaluating Feedback Protocols for Bias in LLM-Based Evaluation" — https://arxiv.org/abs/2504.14716
- Acharya et al. 2026, "RoPoLL: Robust Panel of LLM Judges" — https://arxiv.org/abs/2606.30931

Refinement and self-correction
- Madaan et al. 2023, "Self-Refine: Iterative Refinement with Self-Feedback" — https://arxiv.org/abs/2303.17651
- Huang et al. 2023, "Large Language Models Cannot Self-Correct Reasoning Yet" — https://arxiv.org/abs/2310.01798
- Gou et al. 2023, "CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing" — https://arxiv.org/abs/2305.11738
- Shinn et al. 2023, "Reflexion: Language Agents with Verbal Reinforcement Learning" — https://arxiv.org/abs/2303.11366

Councils, juries and panels
- Verga et al. 2024, "Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models" — https://arxiv.org/abs/2404.18796
- Shaikh et al. 2025, "Collaborative intelligence in AI: Evaluating the performance of a council of AIs on the USMLE" — https://doi.org/10.1371/journal.pdig.0000787
- Sela 2026, "Preserving Disagreement: Architectural Heterogeneity and Coherence Validation in Multi-Agent Policy Simulation" — https://arxiv.org/abs/2604.26561

Deep research and citation faithfulness
- Hirsch et al. 2026, "Who is the Agent to Blame? Localizing Faithfulness and Citation Mistakes in Agentic Deep Research" — https://arxiv.org/abs/2608.24306
- Rao et al. 2026, "Detecting and Correcting Reference Hallucinations in Commercial LLMs and Deep Research Agents" — https://arxiv.org/abs/2604.03173

**Further papers cited by the seats during the review and verified by the orchestrator (8)**

- Kapetanović 2026, "Anchoring Bias in LLM-as-a-Judge Systems: Prior Scores Compromise Evaluation Independence" — https://arxiv.org/abs/2608.25869
- Choi et al. 2025, "Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?" — https://arxiv.org/abs/2508.17536
- Chen, Saha & Bansal 2023, "ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs" — https://arxiv.org/abs/2309.13007
- Zhang et al. 2025, "Stop Overvaluing Multi-Agent Debate — We Must Rethink Evaluation and Embrace Model Heterogeneity" — https://arxiv.org/abs/2502.08788
- Norman et al. 2026, "Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models Across Agreement, Consistency, and Bias" — https://arxiv.org/abs/2606.19544
- Thakur et al. 2024, "Judging the Judges: Evaluating Alignment and Vulnerabilities in LLMs-as-Judges" — https://arxiv.org/abs/2406.12624
- Yang et al. 2026, "Quantifying and Mitigating Self-Preference Bias of LLM Judges" — https://arxiv.org/abs/2604.22891
- Chen et al. 2025, "When and Why Does Multi-Agent Debate Fail and Does It Really Underperform?" — https://arxiv.org/abs/2510.20963

## 1.1.x — 2026-09-08

Public Copilot CLI edition: token discipline (C1–C9), untrusted-content
boundary, STATE_CAPSULE, EVIDENCE_GAP governance, audit manifest, rollback
rule. Specification deliberated in August 2026 by Claude Fable 5 / Gemini
3.1 Pro / GPT-5.6 Sol.
