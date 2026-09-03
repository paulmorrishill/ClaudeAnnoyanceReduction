---
name: design-insufficiency
description: >
  Use when the user wants to find where a feature or screen is badly designed for the person using it —
  NOT whether the code works (adversarial-bug-hunt) or follows conventions (code review), but whether a
  real human can actually DO what they would want to do, and whether the controls and layout make sense.
  Three code-grounded tracks: (1) a static "usability smell" scan keyed to Nielsen's heuristics — raw
  ID/GUID/JSON inputs, text boxes for numbers/dates/enums, rich text shown as a bare textarea,
  view-with-no-edit, unhandled error branches, missing empty/loading states, tables with too many columns,
  rarely-used controls hogging a read-first screen (a whole create form resident on a listing page instead
  of a button → dialog / its own route), controls placed in an arbitrary spot (a homeless lone toggle, a
  filter detached from the list it filters), wrong or missing breadcrumbs, missing or inconsistent padding,
  off-token or unstyled screens, placeholder-as-label, unexplained disabled controls; (2) a role-play
  "cognitive walkthrough" — handicapped personas (mobile field user, new hire, finance/auditor, interrupted,
  wrong-data) trying intents (create, fix a typo, undo, do it 50 times, find it later, hand off) traced
  against the real routes and API contracts to find where the design gives them no path, a dead end, or
  only an insider path; and (3) an archetype capability-completeness diff — classify the feature's kind and
  compare what a feature like it normally has against the code (email with no Subject, import with no error
  report). Triggers — "is this feature well designed", "what would a user struggle with", "find the design
  problems / weird controls / unintuitive bits", "design review", "usability audit", "would a real user be
  able to X", "design insufficiency", "/design-insufficiency". NOT for behavioural bugs
  (adversarial-bug-hunt), NOT for style or convention compliance (code review), NOT for test gaps
  (e2e-coverage-validation), NOT for applying a restyle. Reports; never fixes inline.
---

# design-insufficiency — could a real person actually use this, and do the controls make sense?

## Overview

A code review asks "does this follow the rules". A bug hunt asks "does this break". Neither asks the question this skill exists for: **can a human accomplish what they would reasonably want to do here, and are the controls and layout sane for a person rather than a programmer?** A feature can be bug-free, on-convention, fully tested — and still ask the user to paste a GUID, hide the edit button, show a JSON textarea, dead-end after submit, render a 14-column table on a phone, or spend the top of a listing page on a six-field create form the user needs once a month.

**Screen real estate is proportional to use frequency.** Controls touched on most visits (search, filter, the rows) stay inline; controls touched rarely (create, bulk config, admin settings) belong behind a button → dialog or their own route. That is the H8 progressive-disclosure cluster in [detectors.md](detectors.md), and it is one of the most reliable sources of "this screen feels heavy". Its twin is **placement and grouping** — the right control dumped in an arbitrary spot: a lone toggle floating between unrelated blocks with no container, or a filter rendered nowhere near the list it filters. Generated templates read in the order the developer thought of things, not the order the user reads them; both clusters exist to catch that.

This runs **three** code-grounded tracks that find different classes of problem and barely overlap:

- **Static track (heuristic evaluation).** Grep, AST and contract-join over the front-end code and the API contracts. Deterministic, wide, keyed to Nielsen's 10 heuristics. Catches the objectively weird controls and layout. → **[detectors.md](detectors.md)**.
- **Role-play track (cognitive walkthrough).** **Handicapped** personas × intents, traced against the real route and contract map, prompted to find *where they would give up* — not to complete the task. Catches missing paths, dead ends, insider-only flows. → **[personas.md](personas.md)**.
- **Completeness track (archetype expectation gap).** Classify the feature's *kind* (outbound email, import, CRUD list, scheduler, payment, approval…), build the checklist of what a feature of that kind normally has — from a baked library **plus live internet research** — and diff it against the code. Catches whole capabilities that are simply absent. → **[archetypes.md](archetypes.md)**.
- **Skeptic → Referee.** Every candidate is challenged ("is there actually a path, affordance or capability they missed?") then given a binding verdict. Cross-linked findings — a static "no edit affordance" hit that confirms a role-play "couldn't fix a typo" wall — are promoted.

**Core principle: a finding must name the person, what they wanted, and the exact `file:line` where the design fails them.** "Feels clunky" with no anchor is discarded, not reported.

Grounded in code, always. No imagining screens that do not exist — every persona traces real routes; every smell cites a real control. This skill **reports; it does not fix.**

### Setting it up in your repo

The skill is framework-neutral. Before first use, fill in the `<fill in>` markers in [detectors.md](detectors.md):

- Your **design system**: the shared component prefix, where the components live, the colour/spacing tokens and the file that defines them.
- Your **API contract shape**: where the generated or hand-written clients live, and how a request's field types and a response's error values are expressed. The contract-join detectors are the Tier-A backbone and need this.
- Your **terminology or i18n layer**, if user-visible nouns are configurable per tenant or per locale.
- Your **template syntax**: how conditionals, loops and empty branches are written in your framework.

### Why grounded-in-code, and the one trap to avoid

Research on LLM usability agents (UXAgent, CHI'25) found the model **completes tasks more easily than real humans, takes optimal paths, and spots FEWER failure points** — a naive "can the agent do it" pass is dangerously over-optimistic. Two defences, both baked into this skill:

1. **Handicap every persona** — mobile, interrupted, wrong data entered, no insider knowledge, came back a week later. Force the sub-optimal path a real user takes.
2. **Lean on the static track** for the failures an optimistic walkthrough glosses over — it is deterministic and does not get lucky.

## When to use

- "Is this feature well designed / usable", "what would a user struggle with", "find the weird or unintuitive controls", "design review before we ship", "would a real user be able to \<X>", "/design-insufficiency".
- After a feature is functionally done and tested, before a manual QA or design pass — to hand the reviewer a ranked list of what will feel wrong.
- When a screen "works" but someone senses it is awkward and wants the awkwardness pinned to `file:line`.

**Do NOT use for:**

- "Does it break / race / lose data" → **adversarial-bug-hunt**.
- Naming, structure or convention compliance → a code-review skill.
- "Is it covered by tests" → **e2e-coverage-validation**.
- Pure styling-token drift with no usability judgement → a design-system audit.
- Writing the fix or the restyle → the normal feature flow.

## Step 0 — Verify the scope is current (before anything else)

**A finding is only worth reporting if it is still true on the branch the team ships from.** Audit a stale checkout and you get findings that are real, precise, contract-joined — and fixed upstream weeks ago. Nothing downstream catches it: the Skeptic and Referee read the same stale tree and confirm the finding honestly, because on that tree it *is* true. This is the one error the pipeline cannot self-correct, so it has to be settled here.

```bash
git fetch origin <base branch>                              # whatever the team ships from
git rev-list --left-right --count origin/<base>...HEAD      # behind / ahead
# then, for every file you are about to put in scope:
git diff --quiet HEAD origin/<base> -- <file> || echo "STALE: <file>"
```

- **No scope file differs** → carry on, and record the ref; the report must state what it was audited against.
- **Any scope file differs** → do *not* scan the working tree. Either check the base ref into a worktree (`git worktree add ../audit-base origin/<base>`) and scope the audit there, or merge the base into the working branch first. A branch being "only a bit behind" is not a pass — one merged pull request on the audited screen is enough to invalidate a whole section.

Being behind on files *outside* the scope is fine. It is the scope files that matter.

Pass `baseRef` and `staleFiles` into the workflow; it refuses to run without them, and refuses to run if `staleFiles` is non-empty. If you run the tracks by hand instead, do this check anyway — the cost of skipping it is the entire run.

> Real cost of skipping it: one run over a branch 343 commits behind the base produced a full report and five filed tickets. Four were already fixed on the base — the raw-id text boxes it flagged had been pickers for weeks — and had to be cancelled.

## Step 1 — Resolve the scope and build the route/contract map (always first)

Turn the target into concrete files, and — critically — the **map both tracks share**. Pick the resolver:

| User gives you | Resolve to |
|---|---|
| A **feature** (named) | The route(s) and component(s), the API client(s) they call, the backing server handler(s) |
| A **screen / route** | The component template, styles and code, its child components, the clients it calls |
| A **branch / PR / diff** | `git diff --name-only origin/<base>...<ref>` (or `gh pr diff <n> --name-only`) → the changed front-end files and their clients |
| An **area / folder** | glob the area plus the clients those components import |

Then build the **route/contract map** (this is what makes the tracks grounded, not guessed):

- **Routes** — from the routing configuration: which components are reachable, from where, and the nav depth (for breadcrumbs and orphan detection).
- **Contracts** — for every API client the scope touches, record the request fields **with their types** (id types, enums, boolean, number, string) and the full set of error values (every one is an outcome the UI must handle).
- **Reachability** — which endpoints are reachable from which routes; note any update, edit, delete or archive endpoint whose entity is *displayed* in scope but has **no route or button** to it (the raw material for "view-with-no-edit").

Record the file list and the map. All three tracks consume it.

## Step 2 — Run the three tracks

### Track A — static usability-smell scan (heuristic evaluation)

Read **[detectors.md](detectors.md)** and run each applicable detector over the scope. Each detector = a grep/AST signal plus, where types matter, a contract-join against the map from Step 1. Every finding carries a **confidence tier**:

- **Tier A — deterministic** (type↔control mismatch, unhandled error branch, JSON parsing in a form, orphan update endpoint): report as-is.
- **Tier B — heuristic** (padding, breadcrumb sanity, column count, "weird choice"): Skeptic-filtered and severity-capped; optionally confirm layout ones with a screenshot before reporting.

Prefer the **workflow** template ([design-insufficiency-workflow.js](design-insufficiency-workflow.js)) — one detector-group subagent per heuristic cluster plus one persona-cluster subagent per persona group, pipelined into Skeptic and Referee. Fallback: dispatch subagents by hand, one per detector cluster, in a single parallel message.

> **Passing scope to the workflow — READ THIS or the run scans the wrong feature.** Invoke with `args` as a **real JSON object, not a stringified JSON**. The script defends both ways — it coerces a string arg back to an object, **throws** on an empty `files` scope or an unfilled `map` placeholder, and each track carries a hard scope fence plus a code-level backstop that drops any finding anchored outside `files` (surfaced as `dropped_out_of_scope` in the result). If a run reports findings from an unrelated area, or `scope_file_count: 0`, the scope did not arrive — fix the `args` shape and re-run; do not trust the findings. (History: two early runs silently fell back to an empty scope and fanned 160+ agents across the whole repo instead of the target feature.)

### Track B — persona cognitive walkthrough (role-play)

Read **[personas.md](personas.md)**. For each persona × intent, walk the **real** path from the map: mark each step `available / hidden / missing / requires-workaround`. A **wall** = an intent with no design path, a flow that cannot be completed or exited, or a capability only an insider would find.

Handicap every persona. Prompt them to report **where they would give up**, with the `file:line` of the missing or broken affordance — not a happy-path completion.

### Track C — archetype capability-completeness (classify → expect → diff → verify)

Read **[archetypes.md](archetypes.md)**. Classify the feature into its archetype(s) from the endpoints, the entity, the request shape and the route family. Build the expectation checklist from the baked library **and live internet research** (this track is explicitly allowed to search — use it for unusual, complex or domain-specific archetypes, and to catch expectations the library misses; tag each researched capability with its source URL). Diff every expected capability against the code — present as a request field, an endpoint, a route or a control, or absent? Each absent, plausibly-expected capability is a `[completeness]` candidate, banded **table-stakes / expected / maturity** (do not inflate maturity features to high).

### Cross-link

When findings from different tracks point at the same thing — static "no edit affordance on the detail view" × role-play "wanted to correct a typo, no way in", or a Track C missing capability a persona also hit — **merge them and promote severity.** Independent methods agreeing is the strongest signal this skill produces.

## Step 3 — Skeptic → Referee

- **Skeptic** (per candidate): try to disprove it. Is there a picker sibling you missed? A route to the edit page from a different screen? An error branch handled by a global interceptor? A padding class on a parent? Default to *not disproven* only if you genuinely cannot find the path or affordance.
- **Referee** (per survivor): binding verdict `REAL_GAP` / `HAS_PATH` / `MANUAL_REVIEW` plus one line. `MANUAL_REVIEW` only when it cannot be judged from source (it needs a human eye on the rendered pixels).

## Step 4 — Report

**Output format is fixed. Print the report STRAIGHT INTO CHAT** — a numbered, severity-coded list. No report file, no artifact, no table, unless the user explicitly asks for one.

### Severity codes

Every finding gets an ID: a severity letter plus a running number within that severity, prefixed by that severity's emoji. **One emoji per LEVEL, not per issue** — every High carries the same icon, every Medium the same, every Low the same, so the eye can bracket the list at a glance.

- ⚠️ `H1`, ⚠️ `H2`, ⚠️ `H3` … — **High** (fold anything called `critical` into High and list it first)
- 🟠 `M1`, 🟠 `M2` … — **Medium**
- 🔵 `L1`, 🔵 `L2` … — **Low**

All the `H`s first, then all the `M`s, then all the `L`s. Within a severity, most-severe and highest-confidence first — lead with Tier-A deterministic and cross-linked findings.

Band by what it costs the *person*, not by how sure you are: **High** — they cannot do the thing, lose work, are dead-ended, or are shown something wrong. **Medium** — doable, but only via a workaround, an insider path, or repeated pain. **Low** — works and is findable; it just reads awkwardly.

### Per finding

**Every finding line starts with its SEVERITY emoji** (⚠️ High / 🟠 Medium / 🔵 Low) — the same icon repeated across every finding at that level. Do **not** pick a per-problem icon; a different emoji on each line destroys the banding that makes the list scannable.

Then the ID, then **a short WHERE-clause locating the user in the product before the problem** — "On the invoice-processing screen…", "On the preview dialog after calculating…", "In the booking list…", "On the settings page, Invoice data section…". A `file:line` tells the developer where; the where-clause tells the *reader* which screen and which moment they are standing in. Keep it to a handful of words at the front of the line — never omit it, and never let the `file:line` substitute for it.

Then the problem in one line, then the solution. **Breathe the list out — ONE blank line between the problem and its solution, and TWO blank lines between findings.** Never emit findings as one solid block of text; the whitespace is what makes it readable. If the renderer collapses the double gap, keep the findings visibly separated anyway (a `---` rule between them is the fallback).

**Obvious fix → single line, no options:**

```
⚠️ H1 On the child-detail screen, the Delete button is not wired to anything — it is a placeholder

Solution: Wire in the button


⚠️ H2 On the preview dialog after calculating, …

Solution: …
```

**Genuinely ambiguous, several viable approaches → emoji-lettered options, RECOMMENDED first:**

```
⚠️ H2 Something complicated. Potential solutions:

🅰 something
🅱 something else
```

(Option lines sit together — the blank line goes before 🅰, not between the options.)

**Options use the enclosed-letter emoji, never plain `A)`:** 🅰 🅱 🅲 🅳 🅴 🅵 🅶 🅷 🅸 🅹 🅺 🅻 🅼 🅽 🅾 🅿 🆀 🆁 🆂 🆃 🆄 🆅 🆆 🆇 🆈 🆉

The user replies with the ID plus letter — `H2A` / `H2🅱` / `M3` — and you act on exactly that; accept the plain ASCII letter as equivalent, since it is easier to type. Do **not** manufacture options when one fix is obvious — a single `Solution:` line is the default; options are the exception. 🅰 is always your recommendation.

Each finding also carries, inline after the problem: the `file:line` anchor, the track (`smell` / `role-play` / `completeness` / `both`), the Nielsen heuristic or wall type, and the confidence tier. For `role-play` findings, name the persona and the intent in the problem line ("Mobile field user cannot…").

`MANUAL_REVIEW` survivors go in the list too, with `[needs eyes]` appended to the tag block — say what a human has to look at.

### Tail (after the list)

1. **Scope line** — the base ref the scope was verified against (Step 0), the scope file count, detectors run, personas walked, archetypes classified, anything dropped as not applicable. A report that does not name its base ref cannot be acted on; the reader has no way to tell whether the findings still exist.
2. **`Skeptic/Referee killed N`** — the false-positive count. Do **not** list `HAS_PATH` findings individually, only as this number.
3. **One line telling the user how to reply**: quote the IDs to action, for example `H1, H2B, M3` (plain text — they do not have to type the emoji letters) — and that nothing is fixed until they do. Never fix inline here.

## Common mistakes

- **Auditing stale code** — the most expensive mistake available here, and invisible from inside the run: every track confirms findings that were fixed upstream. Do Step 0 first, every time, and state the base ref in the report. If you filed tickets before noticing, re-verify each anchor against the base ref and cancel the dead ones with the disproving `file:line` — do not leave them in the backlog.
- **Trusting the optimistic walkthrough** — un-handicapped personas complete everything and find nothing. Handicap them and prompt for "where I would give up", or the role-play track is worthless.
- **Imagining screens** — every persona step and every smell must cite real code from the map. No map, no finding.
- **Reporting Tier-B as fact** — padding, breadcrumb and "weird" heuristics are noisy; keep them Skeptic-filtered and clearly tiered, or the user stops trusting the whole report.
- **Skipping the contract-join** — the strongest detectors (raw-ID, text-for-number, enum-as-text, unhandled error) only exist because they compare the request and error types against the control. Grep alone misses them.
- **Overlap with the wrong skill** — behavioural breakage is **adversarial-bug-hunt**; token or style drift alone is a design-system audit. This skill is specifically *human-cannot-do-the-thing* and *control-does-not-make-sense*.
- **Fixing inline** — reports only.
- **Not using the Step 4 format** — no prose write-up, no table, no artifact or file. The numbered ⚠️/🟠/🔵 `H1 / M2 / L3` list in chat *is* the deliverable; it is how the user selects fixes.
- **A different emoji per finding** — the icon marks the SEVERITY LEVEL, not the kind of problem. Vary it per line and the banding that makes the list scannable is gone.
- **Dropping the where-clause** — a `file:line` locates the developer, not the reader. Every finding opens by putting the person on a screen at a moment.
- **Cramming the list together** — one blank line before the solution, two between findings. A solid block of findings does not get read.
- **Padding out the solutions** — inventing 🅰🅱🅲 for a finding with one obvious fix makes the user choose where there is no choice. One obvious fix → one `Solution:` line.
- **Solutions in arbitrary order** — 🅰 must be the one you would actually do, not the first one you thought of. The user reads the order as your recommendation.
