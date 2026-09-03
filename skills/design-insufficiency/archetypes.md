# Capability-completeness by archetype (the "what is normal for a feature like this" track)

The smell track finds bad controls; the role-play track finds blocked intents. **This track finds capabilities that a feature of this *kind* normally has but this one is missing entirely** — the outbound-email screen with no Subject field, the import with no error report, the list with no search.

Method: **classify → expect → diff → verify.**

1. **Classify** the feature into one or more archetypes (from its endpoints, entity and UI).
2. **Expect** — build the checklist of capabilities a feature of that archetype normally has, from the baked library below **plus live internet research** (this track is explicitly allowed to search — use it for unusual or complex archetypes and to catch domain expectations the library misses).
3. **Diff** — for each expected capability, is it present in the code? (a request field, an endpoint, a route, a control). Absent = a candidate gap.
4. **Verify** — the Skeptic checks it is not provided elsewhere, by infrastructure, or deliberately out of scope; the Referee gives the verdict. Severity = how essential the capability is to that archetype.

**Grounded rule:** a gap is only reported against what the code *should* plausibly do. "Missing Subject" on an email sender is a real gap; "missing A/B testing" on an internal password-reset mail is not — the research and the Skeptic separate table-stakes from nice-to-have.

## How to classify

Signals: the endpoint verb and noun (`SendX`, `ImportX`, `CreateX` plus a list, `ScheduleX`, `ApproveX`, `AllocatePayment`…), the entity, the request and response shape, the route family, the existing controls. A feature is often **two** archetypes (an announcement composer is outbound-message + rich-text editor + audience selector); expect against all that apply.

## Severity bands (per capability)

- **table-stakes** — the feature is broken or unsafe without it (an email with no recipient or no subject; an import with no validation; a payment with no amount). Missing = high (there is no "critical" band).
- **expected** — users of this archetype assume it (email preview or test-send; an import error report; list search and filter). Missing = medium.
- **maturity** — good to have, differentiates (email scheduling; import re-map memory; saved filters). Missing = low, report as "consider".

## Baked archetype library (seed — expand with research per run)

### Outbound email / message send

Refs: [Postmark best-practice checklist](https://postmarkapp.com/guides/transactional-email-best-practices/), [MailerSend](https://www.mailersend.com/blog/transactional-email-best-practices).

- **table-stakes**: recipient(s); **subject**; body; a real sender identity; something that actually triggers the send; failure surfaced to the user, not silent.
- **expected**: reply-to that routes to a monitored inbox; cc and bcc; attachments; **preview** before send; **test-send to self**; personalisation fields resolved (no raw `{{name}}` leaking); plain-text fallback; a per-recipient send log or status (sent, failed, bounced); retry on transient failure.
- **maturity**: send-later scheduling; unsubscribe or opt-out that does **not** block account-critical mail; bounce and complaint handling; rate limiting; template management; deliverability awareness.

### CRUD list / index screen

- **table-stakes**: create; row → detail; edit; delete or archive; an empty state.
- **expected**: search; filter; sort; pagination or virtual scroll for unbounded lists; a loading state; permission-gated actions; an archive-versus-hard-delete distinction; a confirm on destructive actions.
- **maturity**: bulk or multi-select actions; column configuration; export; saved views and filters; duplicate or template.

### Import / bulk upload

Refs: [CSVBox file-upload patterns](https://blog.csvbox.io/file-upload-patterns/), [partial imports](https://blog.csvbox.io/partial-import-valid-rows/). The pipeline is **file → map → validate → commit**.

- **table-stakes**: a file picker with accepted formats; format, encoding and delimiter detection; **per-row validation**; a **preview** before commit; the commit itself.
- **expected**: **column mapping** (automatic plus manual for renamed headers); a **downloadable or inline error report tied to row and column with the original value**; partial import (commit the valid rows, quarantine the bad); a progress indicator; idempotency and safe re-run; de-duplication.
- **maturity**: remember the mapping across files; append more files to one session; roll back or undo an import; an audit log of who imported what.

### Scheduler / calendar / assignment

- **table-stakes**: timezone-correct display; create and move an entry; conflicts and overlaps surfaced; past-versus-future edit rules.
- **expected**: recurrence; drag to move with undo; who, what and when visible at a glance; an empty state; a clash or availability check before commit.
- **maturity**: bulk reschedule; templates; optimisation suggestions.

### Payment / billing / money

- **table-stakes**: amount; currency; who is paying and being paid; a confirmation before commit; idempotency (no double charge on retry); the resulting record or receipt.
- **expected**: tax and rounding handled and shown; partial and over-payment handling; refund, void or reverse; an audit trail; export; allocation to invoices or lines.
- **maturity**: reconciliation; multi-currency; scheduled or recurring; dunning.

### Notification / alert (in-app or push)

- **table-stakes**: the trigger; a readable message; a deep link to the thing.
- **expected**: read and unread; opt-out or preferences per channel; de-duplication and batching; do not notify the actor about their own action.
- **maturity**: digest and quiet hours; per-type granularity.

### Approval / review workflow

- **table-stakes**: approve; reject; the resulting state change; a who-can-approve gate.
- **expected**: a reason or comment on reject; an audit trail (who, when, why); notify the requester; view what is being approved in full before deciding.
- **maturity**: delegate; bulk approve; recall or withdraw; multi-step chains.

### Search / find

- **table-stakes**: a query input; results; a no-results state.
- **expected**: debounce; empty-query behaviour; a result count; pagination; clear and reset.
- **maturity**: filters and facets; recent and saved searches; highlighting.

### File attachment / document

- **table-stakes**: upload; accepted type and size enforced and messaged; download; delete.
- **expected**: progress; preview or thumbnail; a per-file error; replace.
- **maturity**: versioning; virus scan; bulk; drag and drop.

### Wizard / multi-step form

- **table-stakes**: a step indicator; next and back; validation per step before advancing; a final commit.
- **expected**: save draft and resume; cancel with confirm; a review-before-submit step; do not lose input on back or navigate-away.
- **maturity**: skip and optional steps; branching; deep link to a step.

### Detail / profile / entity page

- **table-stakes**: the entity's key data; an edit path (this ties to the smell-track "view-with-no-edit").
- **expected**: related entities and links; activity or history; status; actions relevant to the entity.
- **maturity**: inline edit; a timeline; comments and notes.

## Using internet research in this track

For each classified archetype — especially unusual or domain-specific ones the library does not cover — search for:

- `"<archetype> feature checklist"` / `"what should a <archetype> have"` / `"<archetype> best practices"`.
- The two or three category-leading products' feature lists for that archetype.

Fold new capabilities into the expectation checklist, tagged with their source URL, before diffing against the code. Keep table-stakes versus maturity honest — research surfaces many maturity features; do not inflate them to high.

## Output per gap

`archetype | missing capability | band (table-stakes/expected/maturity) | where it should live (endpoint / request field / route / control) | why users expect it | source (library or research URL) | severity (high|medium|low) | where (the screen and moment, in user-facing words) | solutions[] (most-recommended first; ONE if obvious)`.

Feed survivors into the main report tagged `[completeness]`, cross-linkable with role-play walls (a missing capability the persona also hit = `[both]`, promoted).
