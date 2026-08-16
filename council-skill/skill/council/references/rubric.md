# council — scoring rubric and anchors

## Peer-review rubric (Stage 2)

Score each anonymized response 0-100 on each dimension:

| Dimension    | What it measures |
|--------------|------------------|
| Accuracy     | Factual correctness; claims supported by evidence |
| Coverage     | Addresses the whole frozen brief, no dodged criteria |
| Brief-fit    | Delivers the output form the brief asked for (a call for decisions, exact artifact for documents, sourced currency for research) |
| Risk-honesty | Surfaces real assumptions, uncertainties, and counterarguments rather than projecting false confidence |

Rankings are ordinal (1st/2nd) on accuracy + insight combined. Reviewers
judge content only and must ignore any suspected authorship.

## Agreement-score anchors (Stage 4)

Members score the orchestrator's draft against the frozen brief:

| Score  | Meaning |
|--------|---------|
| 90-100 | Publishable as-is. No material error or omission. Any remaining quibbles are editorial. |
| 70-89  | Useful but requires material revision - at least one blocker listed under MATERIAL_BLOCKERS. |
| 50-69  | Major correctness or fitness problem; draft misses or mishandles a core brief requirement. |
| <50    | Fundamentally wrong approach or unsafe/unsupported verdict. |

Calibration rules:

- A score >= 90 REQUIRES `MATERIAL_BLOCKERS: none`. A score < 90 REQUIRES
  at least one concrete entry under `REQUIRED_CHANGES_TO_REACH_90`.
  (This pairing is the anti-sycophancy and anti-stubborn-veto check.)
- Score the draft, not your ego: similarity to your own round-1 answer is
  not a scoring criterion in either direction.
- On Check 2, score the revised draft on its own merits - do not anchor on
  the score you gave Check 1.

## Gate arithmetic (orchestrator)

- PASS = all three fixed seats return a valid integer >= 90.
- Never average, round, infer, or override a score.
- Missing, refused, or twice-malformed = missing; missing can never pass.
- Degraded 2-member council: both remaining >= 90 allows finishing, but the
  report must state that formal (all-three) convergence was not achieved.
