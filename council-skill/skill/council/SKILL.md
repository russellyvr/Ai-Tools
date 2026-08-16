---
name: council
description: Convene an AI Council - three fixed frontier models (Claude Fable 5, Gemini 3.1 Pro, GPT-5.6 Sol) answer a problem independently, anonymously peer-review each other's answers (Karpathy llm-council method), then iterate to strict consensus (every member >=90 agreement, max 2 revision checks) under a clerk orchestrator, ending in a verdict with preserved dissent and a flip condition. Use when the user invokes /council or asks for a council, multi-model opinion, cross-model consensus, a deliberated decision, or a verdict with dissent.
---

# council — AI Council

Deliberate a problem across three heterogeneous frontier models, correct
single-model blind spots via anonymous peer review, and gate the final
answer behind strict all-member consensus (Karpathy llm-council +
llmcouncil.ai: independent answers → anonymized cross-review → synthesis
with verdict / main dissent / flip condition).

## Roster (fixed)

| Role         | Model          | Model ID                 | Effort | Session           |
|--------------|----------------|--------------------------|--------|-------------------|
| Orchestrator | Claude Fable 5 | (main session)           | max    | This conversation |
| Member A     | Claude Fable 5 | `claude-fable-5`         | `max`  | Isolated subagent |
| Member B     | Gemini 3.1 Pro | `gemini-3.1-pro-preview` | `high` | Isolated subagent |
| Member C     | GPT-5.6 Sol    | `gpt-5.6-sol`            | `max`  | Isolated subagent |

Highest effort each model supports. Never substitute models. Auxiliary
research agents are non-voting — never a fourth member.

## Non-negotiable invariants

- The orchestrator is a **clerk and synthesizer, never a judge**: no
  quality scores on member answers (peer reviews are the only quality
  signal); it never answers the problem itself; synthesis stays in the
  orchestrator (no delegated consolidator).
- Same-model conflict (orchestrator = Member A's model) is mitigated, not
  eliminated; disclose in every final report.
- Anonymity holds until the final report. Reviews and scores are never
  shared between members.
- Consensus pass = **all three seats return a valid score >= 90**. Never
  average, infer, or override. Missing/invalid never passes.
- Max 2 consensus push-backs, then final synthesis regardless, dissent
  preserved. Budget: **<=4 substantive prompts per seat** (Round 1, peer
  review, <=2 consensus checks); a prompt may be served by a fresh agent
  of the same model + effort — seat identity = model + effort + verbatim
  written state, not process continuity. Formatting repairs excluded.
- No substantive additions after a passing consensus check.
- Microsoft claims: apply the `ms` skill during consolidation.

## Token discipline (mandatory)

- **Batch & block, never poll (C1):** launch all 3 seats in ONE response;
  collect each stage with parallel blocking `read_agent` (`wait: true`,
  `since_turn` = next unread). No interim narration beyond one short line
  per stage transition. Target <=12 orchestrator tool calls after brief
  freeze (15 with a second check).
- **Per-stage tool budgets (C2):** set in the brief at intake — Round 1 =
  0 tool calls for pure-reasoning briefs; ONE batched round of <=5
  parallel operations for research/code briefs (orchestrator may raise it
  deliberately in the brief). Peer review and consensus are closed-book:
  zero tool calls, single message; sole exception = one read of the shared
  packet artifact.
- **EVIDENCE_GAP governance (C2):** a member believing missing evidence
  would materially change its answer returns `EVIDENCE_GAP: <what>` plus a
  provisional answer anyway. The clerk must then EITHER augment the shared
  packet and rerun the affected stage for all seats, OR carry the gap
  forward as an explicit named assumption printed in the draft, which
  every seat scores at consensus. The clerk never silently arbitrates
  materiality. Unverifiable draft claims at consensus become
  MATERIAL_BLOCKERS, not research excursions.
- **Bounded canonical outputs (C6):** soft caps — Round 1 <=1,200 tokens;
  peer review <=700; consensus reply <=350; STATE_CAPSULE <=300; final
  report uncapped. No restating inputs. Appendix files are for
  NON-MATERIAL support only; material content stays inline under
  `BUDGET_EXCEPTION: <material reason>`.
- **File artifacts (C7):** evidence packet inline when small; above the
  break-even (~3–4K tokens, calibrated from manifest data) write ONE
  immutable file `.copilot/council/<run-id>/packet.md`, record its
  SHA-256, and require a read attestation in Round 1. All run-folder
  artifacts use alias-only filenames; the alias↔identity map lives only in
  private session notes (session SQL) until Stage 5. The orchestrator
  ingests only bounded canonical records, never verbose appendices.
- **Audit manifest (C8):** at end of run write
  `.copilot/council/<run-id>/manifest.md`: per-stage payload sizes,
  per-seat call counts, tool rounds, budget exceptions, agreement scores,
  retained dissent, invariant checklist, artifact hashes. This calibrates
  the C7 threshold and feeds C9 monitoring.

## Procedure

### Stage 0 — Intake gate (exactly one pushback)

1. Compile a **Council Brief**: exact task/decision; ordered criteria;
   evidence + freshness; scope/exclusions; output form; dissent wanted;
   Round-1 tool budget; bracketed default for every unclear field.
2. Push back **exactly once**: echo the brief — "confirm or correct;
   unanswered fields use the bracketed defaults." Complete ask →
   lightweight confirm (never invent questions); else <=5 material
   questions, each with its default.
3. On reply (or "proceed"/silence → defaults), **freeze the brief**. Later
   ambiguities become assumptions or flip conditions — never a second
   interrogation.
4. Build one shared evidence packet (curated facts/assumptions/unknowns,
   file paths or excerpts); inline or artifact per the C7 threshold.

### Stage 1 — Round 1: independent opinions

5. Read `references/prompts.md`. Launch 3 **fresh** background agents in
   one response (`task`, `agent_type: "general-purpose"`,
   `mode: "background"`, per-roster model + effort). Identical prompt:
   frozen brief + packet (or artifact path + read attestation) + tool
   budget + Round-1 contract (ANSWER / REASONING / ASSUMPTIONS /
   STRONGEST COUNTERARGUMENT / FLIP CONDITION / CONFIDENCE, <=1,200 tok).
6. Do not name the roster; do not pre-announce peer review.
7. Collect with blocking reads. Seat failure → retry once, same model +
   effort.

### Stage 2 — Anonymized peer review

8. Build **one common scrubbed bundle (C5)**: all three canonical answers,
   mechanically scrubbed (strip agent/model/vendor identifiers — preserve
   them when they are the substantive subject; **never paraphrase**), each
   tagged with an opaque per-run alias. Record alias↔identity privately
   (session SQL). Each member is told only its own alias and reviews the
   other two.
9. Delivery per seat (C3): if the seat's Round-1 history is lean (<=3
   agentic steps / <~40K), send via `write_agent` (one multi-recipient
   send). If tool-heavy, launch a FRESH same-model same-effort agent fed:
   frozen brief + common bundle + rubric + packet artifact path (one read
   before scoring accuracy).
10. Review contract (`references/prompts.md`, rubric in
    `references/rubric.md`): ranking, anchored scores, errors, ideas worth
    retaining, SELF-REVISIONS, and a **STATE_CAPSULE (C4, <=300 tok)**:
    current stance, key claims with claim/evidence IDs, assumptions,
    strongest counterargument, flip condition, unresolved dissent,
    self-revisions adopted. Peer review does not count as a push-back.

### Stage 3 — Consolidation (claim ledger → Draft 0)

11. Read `references/rubric.md` + `references/output-template.md`. Build a
    compact claim ledger (claim / evidence / supporting responses + peer
    findings / conflicts + resolution). Lean working table only.
12. **Evidence dominates**: peer rankings inform, never mechanically
    weight. Verify checkable claims with local tools. Balanced tie →
    present both positions. No vendor preference.
13. Orchestrator-originated substantive additions must appear in Draft 0.
    Draft 0 is attribution-free, final-report-shaped, and prints any
    carried EVIDENCE_GAP assumptions.

### Stage 4 — Consensus loop (max 2 push-backs)

14. Per seat (C3): persistent if still lean, else FRESH agent fed: frozen
    brief + full draft + compact must-cover claim ledger with unresolved
    items + that seat's own STATE_CAPSULE verbatim — never the full peer
    transcript; packet by path, "read only to verify a blocker."
    Closed-book otherwise. Require the exact schema
    `AGREEMENT_SCORE / MATERIAL_BLOCKERS / REQUIRED_CHANGES_TO_REACH_90 /
    MAIN_DISSENT / FLIP_CONDITION` with the anchored scale. Score against
    the brief, not similarity to their own answer.
15. Malformed → ONE formatting-only repair; still malformed = missing.
16. All three >=90 → Stage 5. Otherwise revise: classify each critique
    corrected / rebutted-with-evidence (tool-verified) /
    preserved-as-dissent; keep a revision log; prioritize blockers and the
    lowest scorer; never revise to flatter. Push Draft 1 + anonymous
    change summary once more: "score this draft on its own merits."
17. After Check 2, stop. All-pass → editorial-only changes. Not passed →
    best synthesis, reported as **not unanimously approved**.

### Stage 5 — Final report

18. De-anonymize only now. Emit the fixed contract from
    `references/output-template.md` (verdict · answer · why · main
    dissent · flip condition · assumptions · status with scores · summary
    table · disclosures). Write the audit manifest (C8).

## Rollback rule (C9)

Monitor fidelity via the manifest. If >=3 councils show warning signs
(consensus needing Check 2 >=2x more often, blockers citing missing
context, dissent loss, unexplained 90-threshold reversals), review — and
where practical decide on paired A/B comparisons on representative briefs
— reverting to persistent agents + strict Round-1 tool caps (the
conservative variant). If platform prefix caching with >=80% discount on
repeated history is confirmed, deprioritize fresh-agent/artifact
indirection (C3/C7) and keep C1/C2/C6/C8.

## Failure policy

- Round-1 seat failure → one retry, same model/effort.
- Mid-loop unresponsive → one nudge / extended wait → relaunch same model
  with the **rehydration prompt** (`references/prompts.md`) containing
  only what that seat was entitled to see → else drop with disclosure.
- A dropped objector's last substantive objection is preserved as dissent.
- Safety refusals preserved, never reprompted around; >=2 refusals → halt
  and report.
- 2 healthy members → continue **degraded** (formal convergence never
  claimable). <2 → abort.
- Disclose every recovery, degradation, or missing stage.

## Acceptance tests

- Underspecified ask → exactly one brief-echo pushback; complete ask →
  lightweight confirm.
- "Proceed"/silence → defaults recorded, protocol runs.
- Each reviewer sees the common bundle, knows only its own alias, reviews
  exactly the other two.
- Scores 94/91/89 → Check 2. Scores 94/91/90 → converged.
- Sub-90 or missing after Check 2 → explicit non-convergence.
- No substantive claim added post-approval.
- Every report has verdict + main dissent + flip condition.
- Degraded run never reports formal convergence.
- Orchestrator never polls; <=12 tool calls post-freeze (15 with Check 2).
- EVIDENCE_GAP is never silently dropped: augment-and-rerun or a printed
  assumption scored at consensus.
- Run folder contains packet (if externalized), alias-named artifacts, and
  the audit manifest.

## Reference loading (progressive disclosure)

| File                            | Load at |
|---------------------------------|---------|
| `references/prompts.md`         | Stage 1 (and repair/rehydration on failure) |
| `references/rubric.md`          | Stage 2 relay and Stage 3/4 scoring |
| `references/output-template.md` | Stage 3 drafting and Stage 5 report |

Do not duplicate template or rubric text inside this file.
