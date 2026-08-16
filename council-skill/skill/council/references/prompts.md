# council — verbatim prompt templates

Use these templates verbatim, filling `<angle-bracket>` slots. Wording
stability across runs matters — do not improvise structure.

## 1. Intake brief-echo (Stage 0)

```
Before seating the council, confirm or correct this brief. Unanswered
fields will use the bracketed defaults.

COUNCIL BRIEF
- Task/decision: <compiled or [default]>
- Decision criteria (ordered): <compiled or [default]>
- Evidence & freshness: <compiled or [default]>
- Scope / exclusions / constraints: <compiled or [default]>
- Desired output (form, depth): <compiled or [default]>
- Dissent to surface: <compiled or [default]>
- Round-1 tool budget: <0 (pure reasoning) | one batched round of <=N ops
  (research/code) or [default]>

Questions (only if material, <=5, each with its default):
1. <question>? [If unanswered: <default>]
```

## 2. Round-1 member prompt (Stage 1)

```
You are Council Member <A|B|C> of an AI Council. Work fully independently.
Do not hedge toward consensus - give your own best answer. Do not attempt
to identify or address other participants.

FROZEN BRIEF:
<frozen Council Brief>

EVIDENCE PACKET:
<inline packet | "Read the packet file at <path> ONCE (SHA-256: <hash>)
and confirm 'PACKET READ' at the top of your reply.">

TOOL BUDGET: <"Do not call tools." | "You may make ONE batched round of up
to <N> parallel tool operations, then answer.">
If missing evidence would materially change your answer, add
"EVIDENCE_GAP: <what is missing>" and still give your best provisional
answer.

Return exactly this structure (<=1,200 tokens; do not restate inputs; if
you must exceed the cap, state "BUDGET_EXCEPTION: <material reason>"):
1. ANSWER - your direct, complete answer. For decisions, make a call, not
   a neutral summary.
2. REASONING - key reasoning steps and evidence.
3. ASSUMPTIONS - assumptions you made.
4. STRONGEST COUNTERARGUMENT - the best case against your answer.
5. FLIP CONDITION - what evidence or change would reverse your answer.
6. CONFIDENCE - 0-100 with one-line justification.
```

Do not name the roster. Do not mention a peer-review stage.

## 3. Peer-review prompt (Stage 2)

One common scrubbed bundle for all reviewers: every canonical answer
tagged with an opaque per-run alias (e.g. R7/K2/M9). Each reviewer is
privately told only its own alias. Persistent seat → send via one
multi-recipient write_agent; tool-heavy seat → launch a fresh same-model
same-effort agent prepending the frozen brief and the packet artifact
path (one read allowed before scoring accuracy).

```
PEER REVIEW STAGE. Below is the anonymized bundle of all council answers
to the problem you answered. Your own answer is the one tagged <alias>.
Review ONLY the other two. Judge content only; if you think you recognize
an author, ignore it. Do not assume any particular models produced these.
Do not call tools<; exception: you may read the packet file at <path>
once>. Reply in a single message.

<common scrubbed bundle: all three canonical answers, verbatim, tagged
with opaque aliases>

Return exactly (<=700 tokens plus the capsule; BUDGET_EXCEPTION allowed):
1. RANKING - rank the two other responses on accuracy, insight, and fit
   to the frozen brief, with brief justification.
2. SCORES - per response, anchored rubric scores (accuracy, coverage,
   brief-fit, risk-honesty; see scale provided).
3. ERRORS/WEAKNESSES - errors, unsupported claims, and gaps in each.
4. IDEAS WORTH RETAINING - strongest elements the synthesis should adopt.
5. SELF-REVISIONS - revisions you would now make to your OWN earlier
   answer having seen these.
6. STATE_CAPSULE (<=300 tokens) - your complete current decision state:
   stance; key claims (with claim/evidence IDs if used); assumptions;
   strongest counterargument; flip condition; unresolved dissent;
   self-revisions adopted. This capsule is the only state guaranteed to
   follow you forward.
```

Include the rubric anchors from `references/rubric.md` inline.

## 4. Consensus-check prompt (Stage 4)

Persistent seat → write_agent; tool-heavy seat → fresh same-model
same-effort agent. Fresh agents receive this prompt with the seat's own
STATE_CAPSULE and the compact claim ledger; never the full peer
transcript or another seat's capsule.

```
CONSENSUS CHECK <1|2>. Below is the orchestrator's consolidated draft,
synthesized from all round-1 answers and all peer reviews. Score it against
the FROZEN BRIEF on its own merits - not on similarity to your own earlier
answer. Do not call tools; sole exception: read the evidence packet at
<path> only if needed to verify a blocker. Reply in a single message
(<=350 tokens; BUDGET_EXCEPTION allowed).

FROZEN BRIEF:
<frozen Council Brief>

<fresh agent only:>
YOUR STATE_CAPSULE (your own prior decision state, verbatim):
<capsule>
MUST-COVER CLAIM LEDGER (incl. unresolved items and any carried
EVIDENCE_GAP assumptions):
<compact ledger>

Scale: 90-100 = publishable, no material error or omission; 70-89 = useful
but requires material revision; <70 = major correctness/fitness problem.

Return EXACTLY this schema:
AGREEMENT_SCORE: <integer 0-100>
MATERIAL_BLOCKERS: <bullets or "none">
REQUIRED_CHANGES_TO_REACH_90: <bullets or "none">
MAIN_DISSENT: <one sentence>
FLIP_CONDITION: <one sentence>

=== DRAFT <v1|v2> ===
<attribution-free draft, incl. any carried EVIDENCE_GAP assumptions>
=== END DRAFT ===
```

For Check 2, additionally prepend: "This draft was revised in response to
council critiques. An anonymous change summary follows. Score this draft
on its own merits." followed by the change summary.

## 5. Formatting-only repair request (administrative)

```
Your previous reply did not match the required schema. Do not change any
substantive content - re-emit your reply in EXACTLY the required schema:
<schema>
```

One repair attempt only; a second malformed reply counts as missing.

## 6. Rehydration prompt (failure recovery)

```
You are Council Member <X> of an AI Council, resuming after a session
interruption. Below is the full record of YOUR OWN prior participation.
Review it and continue exactly where you left off.

FROZEN BRIEF: <brief>
YOUR ROUND-1 ANSWER: <verbatim>
YOUR PEER REVIEW + STATE_CAPSULE: <verbatim, if it happened>
DRAFTS YOU HAVE SEEN: <verbatim, if any>

Next task: <the stage prompt this seat was about to receive>
```

Include ONLY material this seat was entitled to see (its own outputs, the
anonymized texts it already received, drafts already pushed to it). Never
include other members' identities, private reviews, or scores.
