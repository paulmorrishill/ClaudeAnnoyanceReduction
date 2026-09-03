# Background-task monitoring

Paste this into your `CLAUDE.md`. It stops the agent from waiting forever on a background job whose completion notification never arrives.

---

## Background-task monitoring

When starting any long-running background job — a subagent, a background shell command, a workflow — ALWAYS also schedule a backup wakeup that fires regardless of completion notifications.

Reason: completion notifications sometimes fail to arrive (network fault, harness restart, agent produces no output and never returns). Without a backup wakeup, the work stops and the user has to prompt.

### Rule

For every background task, schedule a backup wakeup at roughly `expected_runtime * 1.5`, capped at 1800s.

Examples:

- Quick agent (≤5 min expected) → wake at 300s.
- Medium agent (15 min expected) → wake at 1200s.
- Long agent / full E2E run (25 min expected) → wake at 1800s.
- Multiple parallel agents → use the slowest one's expected runtime.

If the task notification arrives first, the wakeup re-confirms state — cheap. If the task produces no output and never returns, the wakeup catches it.

### On wake — diagnose then act

1. Check whether the task is still running (list the output file, read its last-modified time).
2. If the file has been silent for more than 5 minutes, OR the expected runtime has passed:
   - **Investigate.** Read the last 200 lines of the output file. Identify the last call or tool invoked. Common causes:
     - A test waits for an element that never appears (time the test out, fix the selector).
     - A package install waits on a prompt.
     - A browser driver holds a dead session.
     - A test run waits for a server or dependency that exited.
   - Write the cause in the next response, so the user knows what was slow.
   - If it is safe, stop the task and retry with a tighter timeout and better diagnostic logging.
3. After diagnosing, ALWAYS write a follow-up improvement: a shorter timeout, a better error message, a fake instead of a real network call. The same stop must not happen twice.

### Anti-pattern

Do not wait silently for a completion notification with no backup. Do not ask the user "is it done yet" — schedule a wakeup and check.
