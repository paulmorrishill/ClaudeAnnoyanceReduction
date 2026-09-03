// design-insufficiency pipeline: three tracks -> Skeptic -> Referee -> cross-link.
//   Track A (static smell / heuristic evaluation): one Scanner per Nielsen heuristic cluster (detectors.md).
//   Track B (role-play / cognitive walkthrough): one Walker per handicapped persona cluster (personas.md).
//   Track C (archetype capability completeness): classify -> expect -> diff (archetypes.md).
// All three feed the same Skeptic -> Referee verdict pipeline, then findings are cross-linked.
//
// TEMPLATE — before running via your orchestration tool:
//   1. Run the SKILL.md Step 0 freshness check and pass baseRef + staleFiles (auditing stale code wastes the whole run).
//   2. Fill SCOPE_FILES + ROUTE_CONTRACT_MAP from SKILL.md Step 1 (routes, components, request field types, error values).
//   3. Trim HEURISTICS / PERSONAS to what applies (drop the bulk personas if it is not a list screen).
//   4. Paste the relevant detectors.md rows into DETECTOR_GUIDANCE and the persona rows into PERSONA_GUIDANCE.

export const meta = {
  name: 'design-insufficiency',
  description: 'Static usability-smell scan + handicapped-persona walkthrough + archetype completeness -> Skeptic -> Referee -> cross-link, over one feature scope',
  phases: [
    { title: 'Scan', detail: 'static usability-smell scanner per Nielsen heuristic cluster' },
    { title: 'Walk', detail: 'cognitive walkthrough per handicapped persona cluster' },
    { title: 'Complete', detail: 'classify archetype + diff expected capabilities (research-backed) vs code' },
    { title: 'Skeptic', detail: 'try to disprove each smell/wall/gap (find the path/affordance/capability missed)' },
    { title: 'Referee', detail: 'binding REAL_GAP / HAS_PATH / MANUAL_REVIEW verdict' },
  ],
}

// ---- ARGS NORMALISATION (do not skip) ----
// The orchestration tool delivers `args` as a JS value. If the caller passes it as a JSON *string*
// (an easy mistake), `args?.files` reads undefined and EVERY field silently falls back to its default —
// an EMPTY SCOPE_FILES, which makes every scanner roam the whole repo and audit the WRONG feature
// (this actually happened: a 163-agent run scanned an unrelated area while the target was one wizard).
// Coerce string -> object so args.files and args.map are actually read.
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})

// ---- FILL THESE IN (or supply via args) ----
const SCOPE_FILES = A.files || [
  // 'web/src/app/orders/order-form.component.ts',
  // 'web/src/api/CreateOrder.ts',
]
// FAIL LOUD, never scan nothing: an empty scope is always a caller error, not a valid "scan everything".
// A silent empty-scope run wastes a full fan-out on the wrong code and looks like it worked.
if (!Array.isArray(SCOPE_FILES) || SCOPE_FILES.length === 0) {
  throw new Error('design-insufficiency: SCOPE_FILES is empty. Pass `args` as a JSON OBJECT (not a stringified JSON) with a non-empty `files` array from SKILL Step 1. An empty scope makes every scanner roam the whole repo and audit the wrong feature.')
}
// The route/contract map from SKILL Step 1 — routes, nav depth, request field TYPES, error values.
const ROUTE_CONTRACT_MAP = A.map || '<paste the route list + contract summary here>'
if (ROUTE_CONTRACT_MAP.startsWith('<paste')) {
  throw new Error('design-insufficiency: ROUTE_CONTRACT_MAP is the unfilled placeholder. Supply args.map (the route + request/error contract summary from SKILL Step 1) — without it the tracks are ungrounded and hallucinate screens.')
}
// ---- FRESHNESS GATE (do not skip) ----
// A finding is only worth filing if it is still true on the branch the team actually ships from.
// Auditing a stale checkout produces findings that were fixed upstream weeks ago — they read as
// completely genuine (real file, real line, real contract join) because they WERE genuine, once.
// Nothing downstream can catch this: the Skeptic and Referee both read the same stale tree and
// confirm the finding honestly. It has to be caught here, before any agent runs.
// (History: a run over a branch 343 commits behind the base produced a full report and five filed
// tickets, four of which were already fixed on the base — the raw-id inputs it flagged were pickers.)
const BASE_REF = A.baseRef || null
if (!BASE_REF) {
  throw new Error('design-insufficiency: args.baseRef is missing. Run the SKILL Step 0 freshness check and pass the ref the team ships from (e.g. "origin/develop"), so the report can state what it was audited against.')
}
// staleFiles = the SCOPE files that differ from BASE_REF. Must be supplied (an empty array is the
// pass condition); undefined means the check was never run, which is the actual failure mode.
const STALE_FILES = A.staleFiles
if (!Array.isArray(STALE_FILES)) {
  throw new Error(`design-insufficiency: args.staleFiles is missing. Diff every scope file against ${BASE_REF} and pass the differing paths (pass [] if none). Omitting it means the freshness check was never run.`)
}
if (STALE_FILES.length > 0) {
  throw new Error(`design-insufficiency: ${STALE_FILES.length} scope file(s) differ from ${BASE_REF}, so this run would audit code the team has already moved past. Re-scope onto ${BASE_REF} (check it out into a worktree and scan there, or merge it into the working branch first) and re-run. Stale: ${STALE_FILES.slice(0, 10).join(', ')}${STALE_FILES.length > 10 ? `, +${STALE_FILES.length - 10} more` : ''}`)
}

const STACK_CONTEXT = A.stack || '<front-end framework + design system + how it calls the API>'

// Track A — Nielsen heuristic clusters (detectors.md). Drop any that cannot apply to the scope.
const HEURISTICS = A.heuristics || [
  'H2-real-world (raw ID/JSON/enum-as-text/jargon, hardcoded terminology not via the terminology or i18n layer)',
  'H3-user-control (view-no-edit, no-undo, destructive-no-confirm)',
  'H5-error-prevention (text-for-number/date, rich-text-as-textarea, no-bounds)',
  'H1+H9-status+errors (async-button-no-spinner, long-op-bare-spinner-not-progress, background-job-appears-idle, no-cancel/timeout, no loading/empty/success state, unhandled error branch)',
  'H4-consistency (vendor control where a shared one exists, off-token colour, unstyled screen)',
  'H6+H10-recognition+wayfinding (placeholder-as-label, breadcrumb, orphan route)',
  'H8-layout (too-many-columns, missing/inconsistent padding, cramped)',
  'H8-progressive-disclosure (rarely-used controls eating a read-first screen: create form resident on a listing instead of a button->dialog/own route, per-row inline editor duplicated per row, rare admin/config control permanently above the primary content, primary content pushed below the fold by write controls, multiple unrelated forms on one screen)',
  'H8-placement-grouping (control in an arbitrary spot: homeless lone checkbox/select with no toolbar/filter/group container, filter detached from the list it filters by intervening blocks, template reading-order mismatch, same-job controls scattered instead of grouped)',
  'H8-scalability (per-item control overflow at high N, fixed-slot long text, unbounded list no scroll, seed-data-only layout)',
]
// Track B — handicapped persona clusters (personas.md).
const PERSONAS = A.personas || [
  'field-user-mobile', 'new-hire-day1', 'back-office-bulk',
  'finance-auditor', 'the-corrector', 'the-returner', 'wrong-order-user', 'the-handoff',
]
// Track C — the archetype(s) this feature is. Leave null to let the agent classify from the code.
const ARCHETYPES = A.archetypes || null // e.g. ['outbound-email', 'rich-text-editor', 'audience-selector']
const ARCHETYPE_GUIDANCE = A.archetypeGuidance || '' // pasted archetypes.md checklist rows for the classified kinds
const ALLOW_RESEARCH = A.allowResearch !== false // Track C may search the web for archetype checklists
const DETECTOR_GUIDANCE = A.detectorGuidance || {} // heuristic cluster -> pasted detectors.md rows
const PERSONA_GUIDANCE = A.personaGuidance || {}   // persona -> pasted personas.md row + intents
// -----------------------

// Set of scope files, for the hard scope fence: findings anchored outside these are discarded.
const SCOPE_SET = new Set(SCOPE_FILES)
// The one instruction every track shares — subagents have search and read tools and WILL roam the whole
// repo unless told not to. This is why earlier runs scanned an unrelated area for a one-screen audit.
const SCOPE_FENCE = `
HARD SCOPE FENCE (non-negotiable): The ONLY files you may open, scan, grep, or report on are the scope
files listed above. Do NOT search the wider repo, do NOT wander into neighbouring features, do NOT
report a finding whose file is not one of the scope files. You may read a file named in the route/contract
map for context, but every FINDING you output must anchor to a scope file. If you find nothing in scope,
return an empty findings array — an empty result is correct, roaming out of scope is not.`

// The user picks fixes by ID+letter ("H2B"), so the `solutions` shape is part of the contract, not a nicety.
const SOLUTIONS_RULE = `
SOLUTIONS + SEVERITY + WHERE (contract — the user answers this report with codes like "H2B"):
- where = a short WHERE-CLAUSE locating the USER in the product, not the developer in the tree:
  "On the invoice-processing screen", "On the preview dialog after calculating", "In the booking
  list", "On the settings page, Invoice data section". A handful of words, no file paths — the
  reporter prints it at the front of the finding so the reader knows which screen and which moment they
  are standing in. The file:line is separate and does NOT substitute for it.
- Do NOT emit a per-problem emoji. The report's icon marks the SEVERITY LEVEL (warning/orange/blue), which
  the reporter adds — one icon per level, not per finding.
- solutions[] = the proposed fix(es), ORDERED MOST-RECOMMENDED FIRST (solutions[0] is what you would do).
- If the fix is OBVIOUS, give EXACTLY ONE solution. Do not manufacture alternatives to look thorough
  ("delete button does nothing" -> one solution: wire it up).
- Give 2-3 only when it is a GENUINE judgement call with real trade-offs (different UX, different cost).
- Each solution is one concrete actionable sentence naming the control, route or endpoint — not "improve UX".
- severity is exactly one of high|medium|low (there is NO "critical" band):
  high   = they cannot do the thing / lose work / dead-end / are shown something wrong
  medium = doable but only via a workaround, insider knowledge, or repeated pain
  low    = works and is findable, just reads awkwardly (padding, grouping, wording, polish)`

const FINDINGS_SCHEMA = {
  type: 'object', required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['track', 'file', 'line', 'heuristic', 'problem', 'expected', 'offered', 'severity', 'solutions', 'where'],
        properties: {
          track: { enum: ['smell', 'role-play', 'completeness'] },
          persona: { type: 'string', description: 'role-play only: who hit the wall' },
          intent: { type: 'string', description: 'role-play only: what they wanted to do' },
          file: { type: 'string' },
          line: { type: 'integer' },
          heuristic: { type: 'string', description: 'Nielsen H# / wall_type / archetype' },
          problem: { type: 'string', description: 'the smell or the wall, concretely' },
          expected: { type: 'string', description: 'what a reasonable person expects' },
          offered: { type: 'string', description: 'what the design actually offers (cite the real control/route)' },
          suggested_fix: { type: 'string', description: 'deprecated — use solutions[]; kept = solutions[0]' },
          // Where-clause: the SCREEN + MOMENT the user is standing in ("On the preview dialog after
          // calculating"). Printed at the front of the finding; the file:line does not replace it.
          where: { type: 'string', description: 'short user-facing screen/moment, no file paths' },
          // Ordered MOST-RECOMMENDED FIRST. Exactly ONE entry when the fix is obvious (do not invent
          // alternatives to pad it); 2-3 entries only for a genuine judgement call. The reporter
          // renders these as "Solution:" (one) or lettered options (many) so the user can answer "H2B".
          solutions: { type: 'array', minItems: 1, maxItems: 3, items: { type: 'string' } },
          confidence: { enum: ['A-deterministic', 'B-heuristic'] },
          // Three bands only. high = cannot do it / loses work / dead end / shown something wrong.
          // medium = only via a workaround, insider path, or repeated pain. low = works, just awkward.
          severity: { enum: ['high', 'medium', 'low'] },
        },
      },
    },
  },
}
const SKEPTIC_SCHEMA = {
  type: 'object', required: ['disproven', 'counter_evidence'],
  properties: { disproven: { type: 'boolean' }, counter_evidence: { type: 'string' } },
}
const VERDICT_SCHEMA = {
  type: 'object', required: ['verdict', 'justification'],
  properties: { verdict: { enum: ['REAL_GAP', 'HAS_PATH', 'MANUAL_REVIEW'] }, justification: { type: 'string' } },
}

const fileList = SCOPE_FILES.map(f => `- ${f}`).join('\n')

function scannerPrompt(cluster) {
  const extra = DETECTOR_GUIDANCE[cluster] ? `\nDetectors to run (from detectors.md):\n${DETECTOR_GUIDANCE[cluster]}\n` : ''
  return `You are a static USABILITY-SMELL SCANNER. Scan ONLY for this heuristic cluster: ${cluster}.
Scope files:
${fileList}
Route/contract map (join controls against these TYPES — a control's data type decides the right control):
${ROUTE_CONTRACT_MAP}
Stack: ${STACK_CONTEXT}.${extra}${SCOPE_FENCE}
For EACH smell output: track="smell", file, line, heuristic (H#), problem, expected, offered (cite the
real control/route), solutions[] (the shared component, picker, dropdown or edit route it should be),
where, confidence (A-deterministic for type<->control mismatches, unhandled error branches and orphan
endpoints; else B-heuristic), severity.${SOLUTIONS_RULE}
RULES:
- Cite a REAL file:line IN A SCOPE FILE. No anchor, or an anchor outside scope => discard.
- Contract-join first: compare each control against the request field TYPE and the error values.
- Only this cluster. Return the findings array (empty if none).`
}

function walkerPrompt(persona) {
  const extra = PERSONA_GUIDANCE[persona] ? `\nPersona + intents (from personas.md):\n${PERSONA_GUIDANCE[persona]}\n` : ''
  return `You are ROLE-PLAYING the "${persona}" user. You are NOT trying to complete the task cleverly —
you are trying to find WHERE YOU WOULD GIVE UP, given your handicap.
Scope files:
${fileList}
REAL route/contract map (do NOT invent screens; only walk what is here):
${ROUTE_CONTRACT_MAP}
Stack: ${STACK_CONTEXT}.${extra}${SCOPE_FENCE}
Walk your intents step by step against the real routes and controls. Mark each step
available|hidden|missing|requires-workaround. Stop at the first WALL.
For EACH wall output: track="role-play", persona, intent, file, line (of the missing/broken affordance),
heuristic (wall_type: missing-affordance|dead-end|hidden-path|forced-workaround|unhandled-reverse|context-assumed),
problem, expected, offered, solutions[], where, confidence="B-heuristic", severity.${SOLUTIONS_RULE}
RULES:
- Real file:line IN A SCOPE FILE only. "Feels clunky" with no anchor, or an anchor outside scope => discard.
- If a path MIGHT exist off-map, say so in offered ("verify: possible path via X") and let the Skeptic check — do not assume missing.
- Report where you would GIVE UP, not a completion. Return the findings array (empty if none).`
}

function completenessPrompt() {
  const kinds = ARCHETYPES ? `This feature's archetype(s): ${ARCHETYPES.join(', ')}.` :
    `First CLASSIFY this feature into its archetype(s) from the endpoints, entity, request shape and routes.`
  const research = ALLOW_RESEARCH
    ? `You MAY search the web for "<archetype> feature checklist / best practices" and the 2-3 leading products' feature lists — especially for unusual or domain-specific archetypes. Tag each researched capability with its source URL in its solutions[] entry.`
    : `Use only the baked archetype library guidance below (no web search).`
  return `You are a CAPABILITY-COMPLETENESS analyst. Find whole capabilities a feature of THIS KIND
normally has but this one is MISSING (e.g. an outbound-email screen with no Subject; an import with no
error report). ${kinds}
Scope files:
${fileList}
Route/contract map (endpoints, request fields, routes):
${ROUTE_CONTRACT_MAP}
Stack: ${STACK_CONTEXT}.
Archetype checklist guidance (baked library):
${ARCHETYPE_GUIDANCE || '(none supplied — derive from the archetype + research)'}
${research}${SCOPE_FENCE}
(This track may consult the WEB and read a map-named contract for context, but every reported gap must
still anchor to a SCOPE FILE — where the missing capability should live.)
Method: classify -> build the expected-capability checklist (banded table-stakes/expected/maturity) ->
DIFF each expected capability against the code (present as a request field / endpoint / route / control,
or absent?) -> report each ABSENT, plausibly-expected capability.
For EACH gap output: track="completeness", file (where it SHOULD live — the request, endpoint, route or
component, even though absent), line (best anchor, or the screen/contract file), heuristic=the archetype,
problem (the missing capability), expected (why users of this archetype assume it), offered (what exists
instead, or nothing), solutions[] (+ source URL if researched), where, confidence="B-heuristic",
severity (table-stakes=high, expected=medium, maturity=low).${SOLUTIONS_RULE}
RULES:
- Only report capabilities genuinely EXPECTED for this archetype in THIS context. Do NOT inflate maturity
  features to high. An internal password-reset mail does not need A/B testing.
- Ground every gap: name where it should live. If it might already exist off-scope, say "verify: possibly via X".
Return the findings array (empty if the feature is complete).`
}

const skepticPrompt = (f) => `You are a SKEPTIC. Try to DISPROVE this design-insufficiency claim.
Read defensively: find the picker sibling, the link from another screen, the edit route reachable
elsewhere, the global error interceptor, the parent padding class, the confirm dialog that already exists.
Claim: ${JSON.stringify(f)}
Scope: ${fileList}
Map: ${ROUTE_CONTRACT_MAP}
Set disproven=true only if you genuinely find the path or affordance; cite it (file:line + why) in counter_evidence.`

const refereePrompt = (f, s) => `You are the REFEREE. Independent binding verdict. Re-check the cited code and map yourself.
Finding: ${JSON.stringify(f)}
Skeptic: ${JSON.stringify(s)}
Scope: ${fileList}
Verdict REAL_GAP | HAS_PATH | MANUAL_REVIEW + one-line justification.
MANUAL_REVIEW only when it needs a human eye on rendered pixels to judge.`

const verdictOf = (findingsPromise) =>
  findingsPromise.then(res => parallel((res?.findings || []).map(f => () =>
    agent(skepticPrompt(f), { label: `skeptic:${f.file}:${f.line}`, phase: 'Skeptic', schema: SKEPTIC_SCHEMA })
      .then(sk => agent(refereePrompt(f, sk), { label: `referee:${f.file}:${f.line}`, phase: 'Referee', schema: VERDICT_SCHEMA })
        .then(v => ({ ...f, skeptic: sk, verdict: v.verdict, justification: v.justification }))))))

// All three tracks run in parallel, and each finding flows to Skeptic + Referee as soon as it lands.
const smellRuns = HEURISTICS.map(h => () =>
  verdictOf(agent(scannerPrompt(h), { label: `scan:${h}`, phase: 'Scan', schema: FINDINGS_SCHEMA })))
const walkRuns = PERSONAS.map(p => () =>
  verdictOf(agent(walkerPrompt(p), { label: `walk:${p}`, phase: 'Walk', schema: FINDINGS_SCHEMA })))
const completenessRun = () =>
  verdictOf(agent(completenessPrompt(), { label: 'complete:archetype', phase: 'Complete', schema: FINDINGS_SCHEMA }))

const results = await parallel([...smellRuns, ...walkRuns, completenessRun])
const rawAll = results.flat().filter(Boolean)
// Code-level scope-fence backstop: drop any finding whose anchor is NOT a scope file, so a subagent that
// ignored the prompt fence and roamed cannot leak off-scope findings into the report. Surfaced as a count
// (dropped_out_of_scope) rather than silently — a non-zero value means a scanner wandered.
const all = rawAll.filter(f => SCOPE_SET.has(f.file))
const droppedOutOfScope = rawAll.length - all.length
const surviving = all.filter(f => f.verdict === 'REAL_GAP' || f.verdict === 'MANUAL_REVIEW')

// An agent that ignores the enum and emits "critical" must not silently sort to the BOTTOM (an unknown
// severity ranks last) or land in the Low band. Fold it into high before anything ranks or bands.
for (const f of surviving) if (f.severity === 'critical') f.severity = 'high'

// Cross-link: a smell and a wall at the same file (within a few lines) = two methods agreeing -> promote.
const promote = { high: 'high', medium: 'high', low: 'medium' }
const crossLinked = []
for (const f of surviving) {
  const match = surviving.find(g => g !== f && g.track !== f.track && g.file === f.file && Math.abs((g.line || 0) - (f.line || 0)) <= 8)
  crossLinked.push(match ? { ...f, track: 'both', cross_linked_with: `${match.track}:${match.file}:${match.line}`, severity: promote[f.severity] || f.severity } : f)
}

const sevRank = { high: 0, medium: 1, low: 2 }
const tierRank = { 'A-deterministic': 0, 'B-heuristic': 1 }
// Band first (all H, then all M, then all L), then cross-linked to the top of its band (two methods
// agreeing is the strongest signal), then Tier-A before Tier-B.
const rank = (a, b) =>
  (sevRank[a.severity] ?? 9) - (sevRank[b.severity] ?? 9) ||
  ((b.track === 'both') - (a.track === 'both')) ||
  (tierRank[a.confidence] ?? 9) - (tierRank[b.confidence] ?? 9)

// Assign the chat-facing IDs the user replies with: H1 H2 … M1 M2 … L1 L2 …, numbered from 1 WITHIN
// each band. The reporter must print these verbatim — "H2B" means finding H2, solution option B.
// `emoji` is the SEVERITY-LEVEL icon (one per level, repeated on every finding at that level) — it is
// deliberately NOT a per-problem icon; varying it per line destroys the visual banding.
const BAND = { critical: 'H', high: 'H', medium: 'M', low: 'L' }
const BAND_EMOJI = { H: '⚠️', M: '🟠', L: '🔵' }
function withIds(findings) {
  const n = { H: 0, M: 0, L: 0 }
  return findings.map(f => {
    const band = BAND[f.severity] || 'L'
    return {
      ...f,
      id: `${band}${++n[band]}`,
      emoji: BAND_EMOJI[band],
      solutions: f.solutions?.length ? f.solutions : [f.suggested_fix].filter(Boolean),
    }
  })
}

// REAL_GAP and MANUAL_REVIEW share one ID sequence — they land in one chat list, so numbering them
// separately would emit two H1s and the user's "H1" reply would be ambiguous.
const reported = withIds(
  crossLinked.filter(f => f.verdict === 'REAL_GAP' || f.verdict === 'MANUAL_REVIEW').sort(rank))

return {
  base_ref: BASE_REF, // what the scope was verified current against — quote this in the report
  heuristics_scanned: HEURISTICS,
  personas_walked: PERSONAS,
  archetypes: ARCHETYPES || 'auto-classified by agent',
  scope_file_count: SCOPE_FILES.length,
  scope_files: SCOPE_FILES,
  dropped_out_of_scope: droppedOutOfScope, // >0 means a subagent roamed past the scope fence — investigate
  // THE report list: already banded, ranked and ID'd (H1 / M2 / L3) with `where` + `solutions[]`.
  // Render straight into chat per SKILL.md Step 4 — emoji + id + where + problem, blank line,
  // then Solution: (or the lettered options). Do NOT re-sort or re-number — the IDs are the user's handle.
  findings: reported,
  manual_review_ids: reported.filter(f => f.verdict === 'MANUAL_REVIEW').map(f => f.id), // tag these [needs eyes]
  false_positives_killed: all.filter(f => f.verdict === 'HAS_PATH').length,
}
