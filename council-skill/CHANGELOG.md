# Changelog — council-skill

## 1.2.0 — 2026-09-12 — the council reviews its own specification

On 12 September 2026 this skill's specification was put before a council of
the three vendors' current flagships — **Claude Fable 5.1** (Anthropic),
**Gemini 3.1 Pro** (Google), **GPT-6 Astra** (OpenAI) — with a
deep-research evidence packet: the original Karpathy llm-council source,
current Anthropic / OpenAI / Google documentation on multi-agent
orchestration, LLM-as-judge and deep research, and 26 peer-reviewed papers
on multi-agent debate, ensembles, judge bias and refinement loops. The
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
cannot provide one, the report says so.

## 1.1.x — 2026-09-08

Public Copilot CLI edition: token discipline (C1–C9), untrusted-content
boundary, STATE_CAPSULE, EVIDENCE_GAP governance, audit manifest, rollback
rule. Specification deliberated in August 2026 by Claude Fable 5 / Gemini
3.1 Pro / GPT-5.6 Sol.
