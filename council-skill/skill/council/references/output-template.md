# council — final report template (Stage 5) and disclosure rules

De-anonymize only at this stage. Emit exactly this structure:

```
# Council Final Report

## 1. Verdict
<the call - direct, not a neutral summary>

## 2. Recommended Answer / Action
<the synthesized, self-contained, directly usable solution>

## 3. Why
<key evidence and reasoning that carried the verdict>

## 4. Main Dissent
<the strongest EVIDENCE-BASED surviving counterargument, attributed by
model. The lowest scorer's unresolved blocker must be represented, but a
weak objection is never auto-promoted over a stronger one.>

## 5. Flip Condition
<the specific evidence, event, or assumption-failure that would reverse
the verdict and make the dissent correct>

## 6. Assumptions & Uncertainties
<all intake defaults applied, member assumptions adopted, open unknowns>

## 7. Council Status
<"Converged after Check <1|2>; scores <a>/<b>/<c>" or
 "Not converged after two checks; scores <a>/<b>/<c>; the <lowest>-scorer's
 blocker is preserved under Main Dissent" or
 "Degraded run (2 members); formal convergence not claimable">

## 8. Council Summary
| Member | Model | Round-1 stance | Peer scores received | Final agreement |
|--------|-------|----------------|----------------------|-----------------|

## 9. Disclosures
<standing + incident disclosures - see rules below>
```

## Disclosure rules

Always include:

- **Same-model note (standing, every run):** the orchestrator and Member A
  share a model family; anonymization, the clerk role, peer-only scoring,
  and the unanimity gate mitigate but do not eliminate self-preference.

Include when applicable:

- Seat failures, retries, rehydrations, drops (and that a dropped
  objector's last objection was preserved as dissent).
- Which seats were served by fresh (stage-scoped) agents vs persistent
  conversations, and any BUDGET_EXCEPTION or EVIDENCE_GAP events (with
  how each gap was resolved: augment-and-rerun vs scored assumption).
- Degraded (2-member) runs and the abort rule (<2 members).
- Safety refusals (preserved, not reprompted around).
- Any score treated as missing (malformed twice / no response).
- Evidence rebuttals issued against provably wrong objections, with the
  verification performed.
- Path to the run's audit manifest (`.copilot/council/<run-id>/manifest.md`).

## Revision log (internal, keep during Stage 4)

For each critique across checks record: source seat (by private label),
the critique, classification (corrected / rebutted-with-evidence /
preserved-as-dissent), and the action taken. Summarize material entries
under Disclosures if they shaped the verdict.
