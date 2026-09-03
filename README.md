# ClaudeAnnoyanceReduction

Shared, project-neutral Claude Code instructions and skills. Everything here is generic: no repository, product or stack names, no internal paths. Copy a file into your own repo and fill in the `<fill in>` markers.

Two kinds of thing live here:

- **`claude-md/`** — text to paste into your repo's `CLAUDE.md`. It changes how the agent *writes and behaves*.
- **`skills/`** — full skills to copy into `.claude/skills/`. They change what the agent *can do*.

---

## claude-md/

| File | What it removes |
|---|---|
| [CLAUDE.template.md](claude-md/CLAUDE.template.md) | Everything below, combined into one ready-to-edit `CLAUDE.md`. Start here. |
| [start-of-work-branch-rule.md](claude-md/start-of-work-branch-rule.md) | Work done on a stale or wrong branch. The agent asks one fixed five-option working-tree question before any code. |
| [writing-style.md](claude-md/writing-style.md) | Vague words, self-narration, apology, flattery, "landed", "wedged", editorialising. Simplified Technical English plus a fixed banned-word list. |
| [working-discipline.md](claude-md/working-discipline.md) | Invented time estimates, mid-task stops, schema hacks around migration errors, "✅ passing" over a red build. |
| [background-task-monitoring.md](claude-md/background-task-monitoring.md) | Waiting forever on a background job whose completion notification never arrived. |

### Install

Copy [claude-md/CLAUDE.template.md](claude-md/CLAUDE.template.md) to your repo root as `CLAUDE.md`, replace `<PROJECT>` and `<base branch>`, then fill the "Stack rules" and "Skills" sections with your own documents. Or paste the individual files into a `CLAUDE.md` you already have.

The writing rules stack with terseness modes: terseness controls how many words, these rules control which words.

---

## skills/

Copy a skill directory into `.claude/skills/` in your repo. Each has a `SKILL.md` with frontmatter, supporting reference files, and (where it fans out) a workflow script template.

| Skill | Question it answers |
|---|---|
| [adversarial-bug-hunt](skills/adversarial-bug-hunt/) | *What is latently broken here?* One Hunter subagent per bug class (concurrency, non-determinism, date-time, transactions, N+1, error handling, auth/tenant, front-end async, contracts, resource leaks) → a Skeptic that tries to disprove each finding → a Referee that gives the binding verdict. Reports; never fixes. |
| [e2e-coverage-validation](skills/e2e-coverage-validation/) | *Is this feature actually covered?* Enumerates every branch, error value, permission path and UI state (mutation-test style), enumerates every real test, joins them, and ranks the gaps. A second agent derives the expected scenarios with the code withheld, to catch paths the code forgot. Read-only audit. |
| [design-insufficiency](skills/design-insufficiency/) | *Can a real person use this?* Three tracks — a static usability-smell scan keyed to Nielsen's heuristics, a handicapped-persona cognitive walkthrough, and an archetype capability-completeness diff — then Skeptic → Referee, cross-linked. Reports as a severity-banded list you reply to by ID. |

All three share the same design: **fan out narrowly, then try to disprove.** One agent hunting everything latches onto the first problem class it sees and shares the blind spots of whatever model wrote the code. One agent per class, then an adversarial pass, then an independent verdict, removes both.

### Making them yours

The skills are stack-neutral, so they are honest but blunt out of the box. Each has a short setup section naming what to fill in — the design system, the API contract shape, where the tests live, the framework's template syntax, your real hotspots. Ten minutes of that is the difference between generic advice and findings anchored to `file:line`.

---

## Licence

MIT. See [LICENSE](LICENSE).
