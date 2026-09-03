# Static usability-smell detectors (heuristic evaluation)

Each detector = a **code signal** plus, where types matter, a **contract-join** against the route/contract map from SKILL Step 1. Keyed to Nielsen's 10 heuristics so nothing whole gets missed. `H#` = the heuristic it violates. **Tier A** = deterministic (report as-is). **Tier B** = heuristic (Skeptic-filter, severity-cap, optionally confirm with a screenshot).

## Fill these in before first use

The detectors below are framework-neutral. They get their teeth from four project facts:

- **Contract facts** — where your API clients live, and how they express a request's field **types** (id types, enums, boolean, number, string) and a response's **error values**. Every error value is an outcome the UI must render. _<fill in: client directory, type conventions, the error-to-string mapping if you have one>_
- **Design system ground truth** — the shared component prefix and directory, and the colour and spacing tokens plus the file that defines them. _<fill in>_
- **Terminology / i18n ground truth** — if user-visible nouns are configurable per tenant or per locale, name the service, the pipe or function that resolves them, and the full key list. **Trap:** the default value of each key is usually the English word itself, so a hardcoded noun renders identically in development and is only wrong once a tenant renames it — invisible without this detector. _<fill in, or delete this detector>_
- **Template syntax** — how your framework writes conditionals, loops, empty branches and bindings, so the greps match. _<fill in>_

---

## H1 — Visibility of system status

**Feedback must be proportional to how long the operation takes** — the classic response-time limits ([NN/G](https://www.nngroup.com/articles/response-times-3-important-limits/)): `< 0.1s` feels instant (just show the result) · `< 1s` noticeable but no indicator needed · `1–10s` show *something is happening* (spinner, disabled button) · `> 10s` needs a **determinate percent or step progress indicator and a way to cancel**, and must never look idle. "I clicked and nothing happened" is the single most common design-insufficiency complaint — this cluster is where it lives.

| Detector | Signal | Tier |
|---|---|---|
| **No loading state** | A component issues a request but the template has no pending or spinner branch | B |
| **Async action, no immediate feedback** | A click or submit handler that issues a request, but the trigger control is **not disabled and has no inline spinner** while in flight → looks dead, invites a double click (also a double-submit bug) | A |
| **Long operation shown as a bare spinner** | An operation plausibly longer than about 10s — import analyse/apply, optimisation, AI or LLM call, report, export, any bulk action — rendered with only an **indeterminate** spinner, no percent, step, count or ETA. The user cannot tell progress from a stall. | B |
| **Long or background job appears idle** | A queued, scheduled or long job started with **no status polling** and **no completion notification** → the screen looks like nothing happened; the user re-triggers or navigates away | B |
| **No stall or timeout messaging** | A long wait with no escalation ("still working…") and no timeout or error path if it never returns → an indefinite silent spinner | B |
| **No cancel on a long operation** | An operation over 10s with a progress indicator but **no way to interrupt or cancel** | B |
| **No success feedback** | A create, update, delete or archive request resolves but no toast, banner or notification follows → the user is unsure it worked and repeats it | B |
| **No empty state** | A loop over a list with no empty branch → a blank screen at zero rows | A |
| **Silent async** | A request whose result updates nothing visible on error | B |

## H2 — Match between system and the real world (the "programmer leaked into the UI" smells)

| Detector | Signal | Tier |
|---|---|---|
| **Raw ID / GUID input** | A control bound to a request field typed as an **id** with **no picker sibling** (select, autocomplete, entity list). The user should pick "Acme Ltd", not paste an id. | A |
| **JSON / raw blob input** | A textarea near `JSON.parse`/`JSON.stringify`, or a label or placeholder containing `JSON`, `{`, `config` or `payload` | A |
| **Enum as free text** | A request field typed as an **enum** bound to a text input instead of a dropdown or segmented control. Join the enum fields against the control type. | A |
| **Internal code shown raw** | Displaying an id, ULID or enum **integer** value to the user instead of a mapped label | A |
| **Jargon label** | A field label that is the backend field name verbatim (camelCase or PascalCase in the template) rather than human copy | B |
| **Hardcoded terminology** | A configurable noun rendered as a **literal** in user-visible text — element text, or a title, subtitle, placeholder, empty-message, aria-label or tooltip binding — instead of going through the terminology or i18n layer. Breaks tenants or locales that renamed the noun. Ignore matches in class names, attribute names, route links, message ids and comments. Also flag a hardcoded `a/an <noun>` where the determiner form should be resolved. | A |
| **Term rendered before load** | A terminology-driven label shown without waiting for the terminology to load, where a wrong-term flash matters (breadcrumbs, headings) | B |

## H3 — User control and freedom (undo / edit / exit — the "cannot take it back" smells)

| Detector | Signal | Tier |
|---|---|---|
| **View with no edit** | An update or edit endpoint exists for an entity that is **displayed** in scope, but no route or button reaches it from the detail or list view | A |
| **Read-only field, no edit path** | A field editable on the create form but rendered static on the detail view with no edit affordance anywhere | A |
| **No cancel / back** | A create or multi-step form with no cancel, back or close control | B |
| **Unhandled reverse** | A committed or destructive action (delete, archive, submit) with no update, cancel or undo counterpart anywhere in the module | B |
| **Destructive, no confirm** | A delete or archive triggered directly from a click with no confirmation dialog | A |

## H4 — Consistency and standards

| Detector | Signal | Tier |
|---|---|---|
| **Third-party control where a shared one exists** | A raw framework or vendor component used where your design system has an equivalent | A |
| **Raw HTML control** | A bare `<button>`, or a hand-rolled card, panel or badge, not wrapped in the shared component | A |
| **Off-token colour** | A hardcoded hex, `rgb(` or vendor colour variable in a feature stylesheet instead of a design token | A |
| **Unstyled screen** | A non-trivial template with an empty or absent stylesheet → browser default rendering | A |
| **Inconsistent control for the same job** | Two screens in scope use different controls for the same concept (one a select, one a text box, for the same enum) | B |

## H5 — Error prevention (stop the mistake before it happens)

| Detector | Signal | Tier |
|---|---|---|
| **Non-specific input type** | A request field typed number, money, quantity or percent bound to a plain text input (no numeric type, no numeric input mode, no mask). Also email, phone and url fields as plain text. | A |
| **Date/time as text** | A date- or time-backed field with a plain text input rather than a date picker | A |
| **Rich text as a bare textarea** | A field whose value is **rendered** as HTML or markdown but **edited** as a plain textarea — a round-trip mismatch | A |
| **Multi-line in a single-line control** | A long-form field (description, notes, address) as a single-line input | B |
| **No bounds** | A numeric field with no min, max or step where the domain has them (percent 0–100, positive-only money) | B |
| **Required not signalled** | A required validator in the code with no required marker in the template, or the reverse | B |

## H6 — Recognition rather than recall

| Detector | Signal | Tier |
|---|---|---|
| **Placeholder as label** | A control with a placeholder but no label or aria-label — the label vanishes on type | A |
| **Unexplained disabled** | A disabled binding with no adjacent tooltip, title or hint explaining why → the user is stuck with no reason | B |
| **Truncated, no reveal** | Text truncated by ellipsis or a slice, on a name or description, with no tooltip or expand | B |

## H7 — Flexibility and efficiency (scale and the power user)

| Detector | Signal | Tier |
|---|---|---|
| **No bulk path** | A list where every action is per-row only, for an entity a back-office user would plausibly action in bulk (no select-all or multi-select) | B |
| **No duplicate or template** | A heavy create form for an entity users make many similar copies of, with no duplicate or from-template path | B |

## H8 — Aesthetic and minimalist design (density / layout / spacing)

| Detector | Signal | Tier |
|---|---|---|
| **Too many columns** | Count the column definitions per table; flag more than 8 with no horizontal-scroll container and no column hide or priority — worse on a mobile-reachable route | B |
| **Everything on one screen** | A template with a very high control count or length and no tabs, steps or sections | B |
| **Missing padding** | A card, panel or page-root wrapper with child controls and **no** padding or gutter → elements touch the edge | B |
| **Inconsistent padding** | Sibling sections of the same visual role using **different** padding values or classes — collect the spacing values per repeated block and flag the outliers against the most common value | B |
| **Off-scale spacing** | Hardcoded margins or padding not on the token or spacing scale (`13px`, `7px`) | B |
| **Cramped adjacency** | Two interactive controls with zero gap between them | B |

### H8 (progressive disclosure) — is a rarely-used control eating the screen the user came for?

**The rule: screen real estate is proportional to how often the control is used.** A screen has one primary job (usually *read this list* or *read this record*). Controls the user touches on most visits (search, filter, the rows themselves) belong inline. Controls touched **rarely** — create, bulk config, admin settings, one-off imports — belong behind an **"Add X" button opening a dialog, or their own route.** Rendering a whole create form permanently on a listing screen is redundant noise on every visit but the rare one where it is used: it pushes the actual content down the page, doubles the number of controls the eye has to triage, and makes the screen read as a form rather than a list (Nielsen H8 aesthetic-and-minimalist; NN/G *progressive disclosure*).

Ask per control block: **how many visits out of ten touch this?** Two or fewer out of ten, and it is more than a single control → it should be disclosed, not resident. Read-heavy screens suffer most: a listing is visited constantly and added to occasionally.

| Detector | Signal | Tier |
|---|---|---|
| **Create form resident on a listing** | A create or add block — three or more form controls bound to new-draft state plus a create submit — rendered **unconditionally** (no toggle, no dialog, not its own route) in the same template as the list it appends to. Should be an "Add X" button → dialog, or a dedicated route. | A |
| **Per-row inline editor** | A form (two or more inputs plus a submit) rendered **inside a loop row**, duplicating the same form once per row for an action taken on one row at a time → the list becomes a grid of forms. Should be a row action opening a dialog, or an inline edit toggle for the active row only. | A |
| **Rare admin or config control resident on a read screen** | A settings or tuning control (a look-ahead window, an include-archived toggle, a threshold, a mapping field) rendered permanently above the primary content of a read-first screen, when it is changed rarely. Should sit in a collapsed filter or settings panel, an overflow menu, or the user's saved preference. | B |
| **Content pushed below the fold by write controls** | Count the controls rendered **before** the first data row of the screen's primary list or record. Flag when the write and config controls plausibly out-measure the primary content in vertical space — the user has to scroll past the form to reach what they came for. | B |
| **Multiple unrelated forms on one screen** | Two or more independent create or submit blocks in the same template targeting **different** entities, each with its own submit and its own error banner. Each is a separate task and belongs in its own dialog or route. | B |
| **Modal-worthy flow inlined** | A multi-step or conditional-branch create flow (fields that appear based on a checkbox or enum) inlined into a listing template, so the page silently reflows while the user is reading the list | B |

**Not this detector** (do not double-report): a *dedicated* create or edit route or dialog that is simply long → that is "Everything on one screen" above. A single inline control (one search box, one filter select) on a list → correct design, leave it. An inline add-row on a screen whose *whole purpose* is rapid repeated entry (timesheet, checklist builder, question authoring) → resident is right, because the frequency test passes; say so rather than flagging it.

### H8 (placement and grouping) — does every control sit *where its job is*, in something?

Frequency is only half of it. The other half is **location**: a control can be the right control, correctly disclosed, and still be dumped in a spot that reads as arbitrary. Two failure shapes, both common in generated code because the template is written top to bottom in the order the developer thought of things rather than in the order the user reads them:

- **Homeless control** — a lone checkbox, select or toggle rendered bare between two unrelated blocks, with no toolbar, filter bar, card section or labelled group around it. Nothing tells the user what it belongs to, so it reads as a stray setting someone forgot to put away.
- **Detached from its target** — a filter, toggle or search that governs a collection, separated from that collection by *other* content (banners, a create form, another card), so the cause and effect is invisible. Filters belong immediately above, or in the header of, the list they filter.

| Detector | Signal | Tier |
|---|---|---|
| **Homeless control** | A single interactive control that is a **direct child of a card or page body**, not inside a toolbar, filter, actions, fieldset or labelled section wrapper, with unrelated siblings on either side (a banner, a heading, a form block) | B |
| **Filter detached from its list** | A control whose handler mutates the state feeding a list, but which is rendered **separated from that list** by one or more intervening blocks — a banner, a create form, another card, another heading. Join the state the control sets against the state the list iterates, and measure the blocks between them in the template. | B |
| **Reading-order mismatch** | Template order does not match the order the user needs: write or config controls before the content they act on, error banners rendered above unrelated controls, filters after the list. Report the intended read order. | B |
| **Ungrouped sibling controls** | Two or more controls doing the same job (filters, or view options) rendered in **separate** places rather than one group → the user cannot tell the full set of levers exists | B |

**Not this detector**: a control genuinely scoped to a card that *is* its container (a card whose whole job is that one setting) → fine. A page-level filter bar at the top governing every card below it → correct; only flag it if it is not grouped or labelled as such.

### H8 (scalability) — does the control degrade gracefully as the data grows?

The commonest version: a control looks fine with the one or two items in seed or mock data, then **overflows or breaks once a real tenant has 20 of them.** Judge every per-item control against **realistic N, not seed N.**

| Detector | Signal | Tier |
|---|---|---|
| **Unbounded horizontal per-item control** | A segmented control, tab bar, chip row, button group or pill row whose items come from a loop over a **user-growable** collection (drafts, zones, saved filters, tags) laid out in a row with **no** wrap, horizontal scroll, "+N more" overflow, or dropdown fallback → it overflows at high N | B |
| **Fixed slot, unbounded text** | A name, label or title from user data rendered in a fixed-width control (chip, segment, button, column header) with no truncation or tooltip → a long value breaks the layout | B |
| **Long list, no scroll or pagination** | A loop over an unbounded collection inside a fixed-height or non-scrolling container with no pagination or virtual scroll → the page grows without bound or clips | B |
| **Seed-data-only layout** | Any layout whose correctness depends on the mock or seed count (the fixture shows one or two items) with no strategy for many → flag for a high-N check | B |

## H9 — Help users recognise and recover from errors

| Detector | Signal | Tier |
|---|---|---|
| **Unhandled error branch** | An error value in the API contract that the consumer never renders. Join each error value against the calling component's error handling. Any unreferenced value = the user does the action and gets silence. | A |
| **Generic error only** | The component shows a single "Something went wrong" for a contract with a *specific* multi-value error type — the specific guidance is thrown away | B |
| **No inline validation** | The form submits and only the server rejects; no client-side validation feedback before submit | B |

## H10 — Help and documentation / wayfinding

| Detector | Signal | Tier |
|---|---|---|
| **Breadcrumb wrong** | Breadcrumb segments do not match the route's actual ancestry (hardcoded crumbs, crumb count ≠ route depth, a label mismatched to the parent route title, the last crumb linking to itself). Join the breadcrumb input against the router path. | B |
| **Breadcrumb missing** | A route two or more levels deep with no breadcrumb → the user cannot tell where they are | B |
| **Orphan route** | A reachable component or route not linked from any nav, menu or link → only reachable by typing the URL | A |
| **Back goes nowhere sane** | An action navigates to a route that is not the logical parent of where the user was | B |
| **Ambiguous button** | Buttons labelled `OK`, `Submit` or `Go` with no object, or two buttons with the same label doing different things | B |

---

## Running the detectors

- Start from the route/contract map (SKILL Step 1). The **contract-join** detectors (raw-ID, text-for-number, enum-as-text, rich-text-as-textarea, unhandled error, view-with-no-edit) are the Tier-A backbone — they compare the request and error **types** against the real control, so they are deterministic, not opinion. Do these first.
- Then the grep-only smells (padding, breadcrumb, columns, colours, unstyled). These are Tier B unless a design-system rule already makes them hard (colours and unstyled screens are Tier A).
- For each finding record: `component — file:line — smell — heuristic (H#) — why it hurts the user — suggested fix (the shared component, picker, dropdown or edit route it should be)`. Verify any replacement component you name actually exists in the design system.
- Layout Tier-B findings (padding, adjacency, columns) can be confirmed visually with a screenshot before reporting, to cut false positives.
