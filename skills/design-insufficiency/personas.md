# Persona cognitive walkthrough (role-play track)

Each persona = **role + constraint + emotional state + a handicap**. The handicap is mandatory — an un-handicapped LLM persona completes every task on the optimal path and finds nothing (UXAgent, CHI'25). Every persona is walked against the **real** route and contract map from SKILL Step 1: no imagining screens.

For each persona × intent, mark each step `available / hidden / missing / requires-workaround`, and report the **wall** — the first point they would give up — with the `file:line` of the missing or broken affordance. Report where they would *give up*, not a happy-path completion.

## Persona library (seeds)

Generate variants from these, do not just run the seeds. Rename them to your product's real roles. The distribution skews to the constrained and adversarial ones — that is where the design fails.

| Persona | Role + context | Constraint / handicap | Cares about |
|---|---|---|---|
| **Field user (mobile)** | Out on a job, on a phone, one hand, patchy signal | Small screen, touch, interrupted, no keyboard for GUIDs or JSON | Speed, big tap targets, works with a poor connection |
| **New hire, day 1** | Just given a login, no training, no tribal knowledge | Does not know the jargon, the ids, or where anything lives | Discoverability, plain labels, an obvious next step |
| **Back-office admin (bulk)** | Managing hundreds of records, **many drafts, filters and saved views** | Needs to do the same action 50 times; has far more items than seed data | Bulk actions, templates, search, no per-row grind; **controls that do not overflow at high N** — probe every per-item control against realistic counts, not the one or two in seed data |
| **Finance / payroll** | Approving money, cares about the number being exact | Legally cannot guess; needs the figure and the audit trail | Correct totals, confirmation, undo, export and reporting |
| **Auditor / read-only** | Reviewing after the fact, a week later | Was not there when the data was entered | Find it later, trace who and when, read-only clarity |
| **The corrector** | Realises they typed the wrong thing right after saving | Already committed the action | Edit after submit, undo, cancel |
| **The returner** | Comes back a week later to finish | Lost all in-session context; maybe a half-done draft | Save draft, resume, find what I started |
| **The wrong-order user** | Does the steps in an order the designer did not expect | Enters child before parent, or skips a "required" precursor | Graceful handling, no dead end, a clear precondition |
| **The hand-off** | Needs a colleague to take over or see this | A different login, no shared screen | A shareable link or route, visible state, assignment |

## Intent catalogue (what they might WANT to do)

Walk each relevant intent per persona. The **reverse/repair** and **cross-cut** intents are where design insufficiency lives — the forward path usually works.

- **Forward** — create, or do the main thing; find how to even start it (discovery).
- **Reverse / repair** — undo, edit after submit, delete, correct a typo, cancel a half-done flow.
- **Scale** — do it 50 times, in bulk, from a template or duplicate.
- **Cross-cut** — find it again later, share or hand it off, export it, report on it.
- **Interrupt** — leave mid-task and come back; "what happens to my input if I navigate away".
- **Edge** — partial completion, save as draft, enter data in the "wrong" order.

## Walkthrough prompt (per persona-cluster subagent)

```
You are ROLE-PLAYING a specific user of this feature. You are NOT trying to look clever or
complete the task on the happy path — you are trying to find WHERE YOU WOULD GIVE UP.

Persona: <persona row — role, context, and especially the HANDICAP>
Feature scope + REAL route/contract map (do not invent screens; only use what is here):
<route list + component files + the request field types and error values>

Walk these intents as this persona, staying inside the real routes and controls above:
<relevant intents>

For EACH intent, trace the real path step by step. For each step mark:
  available | hidden | missing | requires-workaround
Stop at the first WALL — the point this persona, with this handicap, gives up or is forced into an
unnatural workaround.

Output JSON per wall:
  - persona: <who>
  - intent: <what they wanted>
  - expected: what a reasonable person expects to be able to do
  - offered: what the design actually offers (cite the real control or route)
  - wall_type: missing-affordance | dead-end | hidden-path | forced-workaround | unhandled-reverse | context-assumed
  - file: file:line of the missing or broken affordance (or the screen where the path should exist but does not)
  - severity: high | medium | low   (three bands only — no "critical". high = cannot do it / loses work /
    dead end; medium = only via a workaround or an insider path; low = works, just awkward)
  - where: a short WHERE-clause putting the reader on the screen at the moment it fails ("On the
    timesheet detail screen after submitting") — no file paths; the file:line does not replace it
  - solutions: [<fix>, …] ordered MOST-RECOMMENDED FIRST. Exactly ONE when the fix is obvious;
    2-3 only for a genuine judgement call. Rendered as 🅰 🅱 🅲 in the report.

RULES:
- Only walls with a real file:line anchor. "Feels clunky" with no anchor = discard.
- Stay grounded in the provided map. If a path might exist off-map, say "verify: possible path via <X>"
  and let the Skeptic check it — do not assume it is missing.
- Report where you would GIVE UP, not a triumphant completion.
```

## Skeptic prompt (per wall)

```
You are a SKEPTIC. Try to DISPROVE this "no path" claim. Read defensively: find the picker sibling,
the link from another screen, the edit route reachable elsewhere, the global error interceptor,
the parent padding class, the dialog that already exists.
Claim: <wall JSON>   Map/files: <scope>
Output: { disproven: true|false, counter_evidence: "<file:line — the path or affordance they missed>" }
Default to disproven=false only if you genuinely cannot find the path.
```

## Referee prompt (per survivor)

```
You are the REFEREE. Independent binding verdict. Re-check the cited code and map yourself.
Wall: <wall JSON>   Skeptic: <skeptic JSON>   Map/files: <scope>
Verdict: REAL_GAP | HAS_PATH | MANUAL_REVIEW  + one-line justification.
MANUAL_REVIEW only when it needs a human eye on rendered pixels to judge.
```
