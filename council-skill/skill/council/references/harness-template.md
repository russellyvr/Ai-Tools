# council — harness template (bind these before your first run)

Revision 2026-09-12 (`[C-n]` = CHANGELOG change list). This file is
platform-neutral. Copy it, fill in the bindings for your CLI, and keep the
filled copy next to the skill as `references/harness.md`. SKILL.md refuses
to dispatch a seat that has no binding here.

## The four verbs

| Verb | Meaning | Copilot CLI default |
|------|---------|---------------------|
| LAUNCH(seat, prompt) | start that seat's isolated session at its pinned model + effort | `task` with `agent_type: "general-purpose"`, `mode: "background"`, `model:` + `reasoning_effort:` from the pinned roster |
| SEND(seat, message) | a later turn into the same session | `write_agent` to that agent |
| FRESH(seat, prompt) | a stateless call to the seat's pinned model with no prior context — used for EVERY consensus check [C-5] | a new `task` with the same `model` + `reasoning_effort` |
| COLLECT(seat) | wait for and retrieve the reply | blocking `read_agent` (`wait: true`) |

Record, per seat: the transport, how the executed model ID is read back
from a reply (it must equal the pinned ID), how usage is read back, and
how continuity is verified on SEND (a resume that comes back under a new
session or with no cached context is a rehydration event). [C-9]

## Tool-profile enforcement (fill in per seat) [C-1]

The untrusted-content boundary is only real if the platform enforces it.
For each seat write down the mechanism, not the intention:

| Seat | Closed-book (peer review, consensus, reasoning briefs) | Research briefs (Round 1 only) | How it is enforced |
|------|--------------------------------------------------------|--------------------------------|--------------------|
| A |  |  |  |
| B |  |  |  |
| C |  |  |  |

Acceptable enforcement: a per-agent tool allowlist / denylist in the
agent definition; omitting tool definitions from an API request; a
platform permission rule or pre-tool hook that denies reads outside the
run's packet and the seat's own directory. NOT acceptable: a sentence in
the prompt, a working-directory change, or a tool the platform "usually"
does not use. If a seat's transport cannot enforce the profile a brief
requires, that seat is unfillable for that operating mode and the run
aborts or the brief is downscaled (SKILL.md, Failure policy).

Private run artifacts (the alias↔identity map, other seats' replies,
drafts, the revision log) must be unreadable by every seat. If the
platform cannot distinguish the orchestrator from a seat, the orchestrator
reads those files through a tool the seats do not hold.

## Caps and ceilings [C-8]

- Per seat: 4 planned substantive requests; hard cap 7 including retries,
  formatting repairs, cap-breach retries, rehydrations and stage reruns.
- Per run: the brief states token, wall-clock and metered-spend ceilings;
  stop on any of them.
- Output caps: where the platform's output limit includes reasoning
  tokens, size the limit for the effort level and treat a reply cut off by
  it as a cap breach (one retry with a larger limit, counted).
- Per-call timeouts and one retry on transient transport errors, per seat.

## Run folder

`.copilot/council/<run-id>/`: `packet.md` (immutable, SHA-256 recorded),
alias-named seat artifacts, `ledger.md` (claims with source passages),
drafts, `revision-log.md`, `manifest.md`; the alias↔identity map lives
only in private session notes until Stage 5. Append one line per run to
`.copilot/council/score-history.tsv`. [C-10]

## Preflight (Stage 0, before any dispatch)

1. Catalog read and roster resolved; tier conflicts recorded. [C-4]
2. Each seat's tool profile confirmed enforceable for the brief type. [C-1]
3. Run folder writable; packet hashed.
4. Any platform probe uses an ID read from the live catalog, never typed. [C-9]
