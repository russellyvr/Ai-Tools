# council — final report template (Stage 5) and disclosure rules

Revision 2026-09-12 (`[C-n]` = CHANGELOG change list).

De-anonymize only at this stage. Emit exactly this structure:

```
# Council Final Report

## 1. Verdict
<the call - direct, not a neutral summary; conditional on any
decision-critical assumption the source check could not close>

## 2. Recommended Answer / Action
<the synthesized, self-contained, directly usable solution>

## 3. Why
<key evidence and reasoning that carried the verdict>

## 4. Main Dissent
<the strongest EVIDENCE-BASED surviving counterargument, attributed by
model. Any outstanding FACT or SAFETY blocker must be represented, but a
weak objection is never auto-promoted over a stronger one.>

## 5. Flip Condition
<the specific evidence, event, or assumption-failure that would reverse
the verdict and make the dissent correct>

## 6. Assumptions & Uncertainties
<all intake defaults applied, member assumptions adopted, EVIDENCE_GAPs
carried forward, open unknowns>

## 7. Council Status
<"Unanimously approved after Check <1|2>" or
 "Approved by two seats after Check <1|2>; preference dissent preserved
 (<seat>)" or
 "Not unanimously approved after two checks; <seat>'s <FACT|SAFETY>
 blocker is preserved under Main Dissent" or
 "Not unanimously approved; Check 2 skipped because nothing material
 changed after Check 1" or
 "Degraded after post-Round-1 seat loss; approval not claimable" or
 "Aborted before full Round 1: <which seat failed and why>" or
 "Aborted after Round 1: fewer than two seats">
Diagnostic agreement scores per check: <a>/<b>/<c> (Check 1), <a>/<b>/<c> (Check 2).

## 8. Council Summary

Resolved roster (pinned at Stage 0, immutable for this run):

| Seat | Vendor | Model (pinned = executed) | Effort | Resolved via | Tier conflict |
|------|--------|---------------------------|--------|--------------|---------------|
| A | Anthropic | <model id> | <effort> | <catalog | researched | unfillable> | <none | flagged: <newer id>, <choice and reason>> |
| B | Google | <model id> | <effort> | <catalog | researched | unfillable> | <…> |
| C | OpenAI | <model id> | <effort> | <catalog | researched | unfillable> | <…> |

| Member | Model | Tool profile / research tools worked? | Round-1 stance | Peer scores received | Verdicts (Check 1 / Check 2) |
|--------|-------|---------------------------------------|----------------|----------------------|------------------------------|

## 9. Disclosures
<standing + incident disclosures - see rules below>

Manifest: `.copilot/council/<run-id>/manifest.md`
```

## Disclosure rules

Always include:

- **Roster resolution (standing, every run):** the pinned model ID, the
  executed model ID verified from replies, effort per seat, the resolution
  method for each (live catalog vs researched-and-requested), any tier
  conflict with the choice made, and any unfillable seat. [C-4] [C-9]
- **Same-model note (standing, every run):** name any seat whose model
  family matches the orchestrator's; masking, the clerk role, peer-only
  scoring, and the unanimity gate mitigate but do not eliminate
  self-preference; masking cannot remove self-recognition, and the
  structured rubric is a measured but context-dependent mitigation. If no
  seat matches, state that explicitly. [C-7]
- **Tool profile and attestation:** the profile in force per seat, any
  granted exceptions with justification, and whether each seat's research
  tools actually worked. [C-1] [C-3]
- **Source check:** how many draft claims were verified against their
  cited passage, how many were removed or relabelled, and any
  decision-critical assumption the verdict is conditional on. [C-2]
- **Per-seat request counts** against the planned/hard caps, cap-breach
  retries, and per-seat usage (input, cached, reasoning, output) where the
  platform reports it. [C-8]
- **Identity-masking limits:** mechanical scrubbing is identity MASKING,
  not anonymity; a passing gate means unanimous publication approval
  under the rubric, not established truth; the council's accuracy over a
  single grounded model was measured once (pilot 1, 2026-09-12: no gain on
  nine briefs the single model already answered correctly) and remains
  unproven on harder briefs. [C-11]
- **Manifest path** and the score-history line written. [C-10]

Include when applicable:

- Seat failures, retries, cap breaches, lost continuity, rehydrations,
  drops (and that a dropped objector's last objection was preserved as
  dissent).
- Which seats were served by fresh (stage-scoped) agents vs persistent
  conversations, and any BUDGET_EXCEPTION or EVIDENCE_GAP events (with
  how each gap was resolved: augment-and-rerun vs judged assumption).
- Any seat whose model was researched rather than read from a catalog,
  and any seat left unfillable because its vendor exposed no flagship tier
  or its transport could not enforce the required tool profile.
- Degraded (2-member) runs and the abort rule (<2 members).
- Safety refusals (preserved, not reprompted around).
- Any verdict treated as missing (malformed twice / no response).
- Evidence rebuttals issued against provably wrong objections, with the
  verification performed.
- Post-check editorial edits (verified corrections applied after the last
  check), explicitly marked as unscored by any member.
- Suspected injection attempts and scrub escape counts.

## Revision log (internal, keep during Stage 4)

For each critique across checks record: source seat (by private alias),
the critique and its member-assigned category (FACT / SAFETY /
PREFERENCE), classification (corrected / rebutted-with-evidence /
preserved-as-dissent), and the action taken. The anonymous objection
ledger sent with Check 2 is derived from this log. Summarize material
entries under Disclosures if they shaped the verdict.
