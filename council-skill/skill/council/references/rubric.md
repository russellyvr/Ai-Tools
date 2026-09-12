# council — scoring rubric and anchors

Revision 2026-09-12 (`[C-n]` = CHANGELOG change list).

## Peer-review rubric (Stage 2)

Score each anonymized response 0-100 on each dimension:

| Dimension    | What it measures |
|--------------|------------------|
| Accuracy     | Factual correctness; claims supported by evidence. Includes **source fidelity**: cited sources exist and actually support the claim; unsourced claims presented as fact count against accuracy. [C-3] |
| Coverage     | Addresses the whole frozen brief, no dodged criteria |
| Brief-fit    | Delivers the output form the brief asked for (a call for decisions, exact artifact for documents, sourced currency for research) |
| Risk-honesty | Surfaces real assumptions, uncertainties, and counterarguments rather than projecting false confidence |

Ranking (1st/2nd on accuracy + insight combined) is optional and ties are
allowed; absolute scores are the signal the synthesis uses. Reviewers judge
content only and must ignore any suspected authorship. Length is not
quality. [C-7]

## Consensus verdict anchors (Stage 4) [C-5]

Members judge the orchestrator's draft against the frozen brief, in a fresh
context, with the evidence packet and cited passages supplied:

| Verdict | Meaning |
|---------|---------|
| APPROVE | Publishable as-is. No material error or omission. Any remaining quibbles are editorial and are NOT listed as blockers. |
| REVISE  | Not publishable. At least one blocker listed, each linked to the claim or section it concerns and labelled by the member as FACT (a verifiable error or unsupported claim), SAFETY (a risk the brief's constraints forbid), or PREFERENCE (a judgment the member would make differently). |
| ABSTAIN | The member cannot judge (e.g. refusal, missing evidence it names). Never a pass. |

AGREEMENT_SCORE (0-100) is still reported as a diagnostic so borderline
confidence stays visible: 90-100 = publishable, 70-89 = useful but requires
material revision, 50-69 = major correctness or fitness problem, <50 =
fundamentally wrong approach. It does not decide the gate.

Calibration rules:

- APPROVE REQUIRES no active blocker. REVISE REQUIRES at least one
  concrete, claim-linked entry under BLOCKERS and the changes that would
  clear each under REQUIRED_CHANGES. (This pairing is the anti-sycophancy
  and anti-stubborn-veto check.)
- Any draft claim you cannot trace to the supplied evidence or a
  resolvable source is a FACT blocker. [C-2]
- Judge the draft, not your ego: you are not shown your own earlier
  answer, and similarity to it is not a criterion in either direction.
- On Check 2, judge the revised draft on its own merits from the
  objection ledger; you are not shown any prior score.

## Gate arithmetic (orchestrator)

- PASS = all three fixed seats return a valid APPROVE. An APPROVE with an
  active blocker is contradictory: one schema-consistency repair, then it
  counts as REVISE. ABSTAIN, refused, missing, or twice-malformed = never
  passes.
- A FACT or SAFETY blocker from any seat is never overridden by the other
  two. Two valid APPROVEs plus a third seat whose only remaining blockers
  are self-labelled PREFERENCE = "Approved by two seats; preference dissent
  preserved" — a distinct status, never reported as unanimous.
- The orchestrator never relabels a member's blocker category.
- Never average, infer, or override a verdict or score. A stale verdict
  never applies to a revised draft.
- Display raw peer-score vectors and per-check verdicts with diagnostic
  scores in the final report; never aggregate them into an invented
  composite.
- Degraded 2-member council (post-Round-1 loss only): both remaining
  APPROVE allows finishing, but the report must state that formal
  (all-three) approval was not achieved.
