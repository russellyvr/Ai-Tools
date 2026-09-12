# Paired evaluation — pilot 1 (2026-09-12)

The acceptance tests in `SKILL.md` require a paired evaluation before the
council may claim any accuracy over a single grounded model (change C-11
of the 2026-09-12 self-review). This is the first pilot. It was run by the
author's reference implementation of this specification on 12 September
2026 with the three vendors' catalog flagships of that day — **Claude
Fable 5.1** (Anthropic), **Gemini 3.1 Pro** (Google), **GPT-6 Astra**
(OpenAI) — at maximum reasoning effort, the Anthropic model also acting as
the clerk.

## Design

Nine closed-book reasoning briefs with tool-verified answers. Five are
ordinary (a statutory calculation, a documented product limit, an
operating-system failure mode, an API behaviour, a rule-application
decision); four are adversarial, meaning the intuitive answer is wrong
(a reasoning-token accounting rule, a near-threshold statutory case, a
shell-version assumption, an API error class that looks like a rate
limit). Every brief was answered once and the stages were snapshotted as
arms, so the arms share the same Round-1 answers:

| Arm | What it measures |
|-----|------------------|
| S | one grounded single-model answer (the Anthropic seat alone, closed-book) |
| C | three independent answers plus the clerk's synthesis, no review |
| P | C plus masked peer review, then the clerk's Draft 0 |
| K1 | P plus one fresh-context consensus check |
| K2 | P plus up to two checks — the full protocol |

Scoring: an arm is *correct* when its final answer meets the brief's
tolerance; a *false veto* is a check that blocks a draft whose answer is
correct; a *false approval* is a check that approves a wrong one. Brief
001 had been run earlier that day as the protocol shakedown and is
included for arm K2 only.

## Results

| Arm | Briefs | Correct | Approved by all three seats | False vetoes | False approvals |
|-----|-------:|--------:|---------------------------:|-------------:|----------------:|
| S | 8 | 8 | — | — | — |
| C | 8 | 8 | — | — | — |
| P | 8 | 8 | — | — | — |
| K1 | 8 | 8 | 0 | 8 | 0 |
| K2 | 9 | 9 | 3 | 6 | 0 |

Per brief (K2 column: verdicts at the final check, Anthropic / Google / OpenAI):

| Brief | Adversarial | S | K2 answer | Final check | Status |
|-------|:-----------:|:-:|:---------:|-------------|--------|
| 001 statutory length-of-service pay | | — | correct | A95 / A100 / A99 | unanimous after Check 2 |
| 002 named-location limits | | correct | correct | A94 / A100 / A100 | unanimous after Check 2 |
| 003 launchd redirect on an external volume | | correct | correct | A90 / A100 / R75 | not unanimous |
| 004 `instructions` across chained responses | | correct | correct | A93 / A100 / R75 | not unanimous |
| 005 roster rule under a tier conflict | | correct | correct | A90 / A100 / A98 | unanimous after Check 2 |
| 006 thinking tokens and the output cap | yes | correct | correct | A92 / A100 / R82 | not unanimous |
| 007 statutory pay just under a threshold | yes | correct | correct | A95 / R80 / R95 | not unanimous |
| 008 `mapfile` in the stock shell | yes | correct | correct | A95 / A100 / R92 | not unanimous |
| 009 liveness gate versus exhausted credit | yes | correct | correct | A94 / A100 / R85 | not unanimous |

(A = APPROVE, R = REVISE, number = diagnostic agreement score.)

## What the numbers say

- **No accuracy gain was measurable.** The single grounded model answered
  all eight briefs correctly, including the four adversarial ones, so no
  arm could show a wrong-to-correct change and none produced a
  correct-to-wrong change. These briefs were too easy for the current
  flagships to separate the arms; the next pilot needs briefs on which the
  single model fails.
- **The council's value showed up in review, not in the answer.** Peer
  review caught, and kept out of every draft: a mis-cited statutory
  subsection and a confidently wrong account of the statute's structure
  (Google seat, brief 007); an impossible diagnostic test (Google seat,
  brief 003); a false claim that a documented API endpoint does not exist
  (Google seat, brief 009); a Chat-Completions parameter name in a
  Responses-API answer (Google seat, brief 004); and, from the Anthropic
  seat's own check, a real gap in a fix (brief 003: the in-job redirect
  needs its own consent). Every one of these came from a seat that had
  the amount or the call right.
- **The unanimity gate blocked correct answers most of the time.** Six of
  nine full-protocol runs ended "not unanimously approved" with a correct
  answer. Two causes, both structural rather than judgemental:
  1. The consensus-check anchor said any claim not traceable to the
     supplied evidence is a FACT blocker. On closed-book briefs there is
     no supplied evidence, so the OpenAI seat — applying the rule as
     written — vetoed correct RECALL-labelled answers on every check it
     could. Fixed in 1.2.3 (see below).
  2. The fixture packet carried the orchestrator's own labelling
     instruction ("answer from knowledge and label every claim SOURCED or
     RECALL") inside the untrusted-data fence. The Google seat, applying
     the injection rule as written, raised SAFETY blockers against the
     packet and against drafts that "acted on" it. Fixed in 1.2.3 (the
     orchestrator's instructions never travel inside a fence).
- **Where the clerk supplied verified evidence, the vetoes narrowed.** On
  briefs 006, 007, 008 and 009 the clerk added a dated verification
  passage (a live API probe, the statute text, a shell transcript, an
  observed error envelope) before Check 2. The OpenAI seat then accepted
  every core answer and confined its blockers to generalisations beyond
  the passage — defensible objections, several of which improved the
  drafts.
- **Cost.** 72 seat requests over eight briefs (9 per brief; one Anthropic
  Round-1 call was relaunched after a long stall and the duplicate
  discarded). Metered usage as recorded from the API envelopes — Google
  seat: 32 calls, 57.7 thousand prompt tokens, 106 thousand thinking
  tokens, 13.4 thousand output tokens. OpenAI seat: 32 calls, 110 thousand
  input tokens, 217 thousand output tokens of which 205 thousand were
  reasoning. The Anthropic seat ran in-session. Wall-clock for the whole
  pilot, run in overlapping batches, was about three hours; one brief run
  alone takes roughly 20–35 minutes end to end.

## Changes adopted from this pilot (1.2.3)

- **C-14 — Closed-book traceability.** The check anchor now binds claims
  presented as sourced; a RECALL-labelled claim on a closed-book brief is
  judged on the member's own knowledge, never merely on the absence of a
  passage. `references/prompts.md` §4, `references/rubric.md`, and Stage
  4 step 17.
- **Orchestrator instructions never inside a fence.** Output-form and
  labelling rules travel in the prompt body; a fenced line that restates
  them is data to note, not an injection. Untrusted-content boundary.
- **Seat-directory staging.** Every prompt a file-reading seat must open
  is written inside that seat's own directory; the read gate denies the
  run root and did so once during the shakedown.
- **Wall-clock ceiling enforced.** The ceiling is checked before every
  dispatch after Round 1 and stops the run; it had only been disclosed.
- **Billing stop distinguished from rate limit.** A 429 with an
  insufficient-quota code is handled as a transport loss requiring
  top-up, not retried on `Retry-After`; the liveness gate cannot detect
  it.
- **Fixture.** Nine labelled briefs, the arm design above, a score sheet
  and an aggregator ship under `fixtures/paired-eval/` in the reference
  implementation; the answers remain marked as not yet confirmed by the
  owner.

## What this pilot does not show

It does not show that the council is more accurate than a single
grounded frontier model; on these briefs it could not, because the single
model was already right every time. It does not measure fresh-context
versus stateful checks or the categorical versus numeric gate, which
remain separate arms for a later run. The answers were labelled by the
orchestrator from tool-verified sources and are not yet owner-confirmed,
so every row in the score sheet is provisional.
