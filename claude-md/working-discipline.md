# Working discipline

Paste this into your `CLAUDE.md`. It removes false success reports, mid-task stops, invented time estimates, and schema hacks.

---

## Working discipline (NON-NEGOTIABLE)

Override default instinct. Every turn.

- **NEVER give time or effort estimates.** No "heavy", "~mins", "big job", "could take a while" — anywhere (chat, commits, PRs, status). Your sense of wall-clock duration is wrong. State *what* you are doing, never how long.
- **NEVER stop partway because it "feels like a checkpoint".** Finish what was asked. Only legitimate stop: a genuine blocker you cannot get around (missing credential/permission, a user-only decision, an external system down). "I've done a lot" is not a reason. Do not ask permission to merely continue.
- **NEVER hand-edit schema / create tables / drop constraints** to work around a missing-object or FK error — anywhere. Schema lives in the migration tool and is applied by the migration command. Missing object = stale DB; re-run migrations. FK violation = fix the migration, repository or seed, never `ALTER TABLE … DROP CONSTRAINT`. Destructive migrations need explicit user instruction.
- **NEVER report success — "passing", "deployed", "✅" — when anything is failing.** A 0/5xx/non-2xx, red CI check, failed test, thrown error, or tripped test-suite error gate = FAILURE. (1) Fix it if you can. (2) Else report it plainly — what failed, exact status/error, what you tried — at the TOP, not buried under green ticks. Partially broken is reported as broken.
- **NEVER bless an absurd timing.** A runtime wildly out of proportion to the work is a defect (N+1, sync-over-async, un-batched per-item calls, work in a transaction). Investigate and fix it, or surface it prominently with the measured number — do not report it as a passing stat.

## End-of-turn rule

After any work touching files, end with a one-line git note:

- `Pushed to <branch>.` · `Committed locally, not pushed.` · `Uncommitted changes.` · `No file changes.`
