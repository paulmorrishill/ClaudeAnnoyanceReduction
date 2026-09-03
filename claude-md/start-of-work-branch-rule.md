# Start-of-work branch rule

Paste this into your `CLAUDE.md`. It stops the most expensive silent failure available to an agent: doing correct work on a stale or wrong branch. Findings are real, the code is right, and all of it is against a tree the team moved past weeks ago.

---

## Before ANY work — settle the working tree first

Do this **before** you read code for a task, plan, edit a file, run a build, or start an audit. It comes before every other step, including exploration.

1. Fetch the base branch the team ships from: `git fetch origin <base branch>` (`develop`, `main`, or whatever this repo uses).
2. Measure the current state:
   ```bash
   git rev-parse --abbrev-ref HEAD
   git rev-list --left-right --count origin/<base>...HEAD   # behind<TAB>ahead
   git status --porcelain                                   # uncommitted work
   ```
3. **Ask the working-tree question, and wait.** This is the first question of the task — before any plan, any file read for the task, and any code.

### The working-tree question (fixed shape)

Print the state line, then the five options, then stop and wait for a number:

```
What working tree? Current branch is <branch> and is <N> commits behind <base branch>.

1. New branch from latest <base branch> here
2. Pull latest <base branch> and work here
3. Work directly on the existing working files, no branching, no new work tree
4. Create a work tree and pull latest <base branch>
5. Other
```

Rules for the question:

- Ask it **once**, at the start of the task. Do not re-ask it every turn.
- Keep the numbers and the order fixed, so the user can answer with a single digit.
- Fill `<branch>`, `<N>` and `<base branch>` with the measured values. If the branch is up to date, say `0 commits behind`.
- `5. Other` means the user names a branch, a ref, or a different arrangement. Do what they say.
- Wait for the answer. Do not pick a default and continue.

### What each option means

| Option | Commands |
|---|---|
| 1 — New branch from latest base | `git fetch origin <base> && git checkout -b <work branch> origin/<base>` |
| 2 — Pull latest base and work here | `git pull --ff-only` on the current branch (or merge the base in, if the user says so) |
| 3 — Work on the existing files as they are | Change nothing about the branch. State the behind-count once and carry on. |
| 4 — Work tree | `git worktree add <path> -b <work branch> origin/<base>`, then work in that path |
| 5 — Other | The user names it. |

**Never merge, rebase, force-push, reset, stash or discard the user's work** to "get current" without the user's explicit word. Fetching and reporting is always safe. Changing the working tree is not.

If the user picks option 3 on a stale branch, that is their decision: state the behind-count in one line and continue. Do not raise it again.

### Why

- Work built on a stale base collides at merge time, and the collision surfaces long after the reasoning that produced the code is gone.
- Audit and review output is worse: every finding is precise, anchored, and already fixed upstream. Nothing downstream catches it, because a skeptic pass reading the same stale tree confirms the finding honestly. On that tree it *is* true.
- A single merged pull request on the file you are working in is enough to invalidate the whole task. "Only a bit behind" is not a pass.

### Report line

State the base and the freshness in the first message of the task, in one line:

`FACT: on <branch>, 0 behind / 3 ahead of origin/<base>.`

An audit or review report that does not name the ref it was checked against cannot be acted on — the reader has no way to tell whether the findings still exist.
