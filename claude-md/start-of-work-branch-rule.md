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
3. **Classify the request as read-only or write** (§ 1), then follow that branch.

---

## 1. Classify the request first

Read-only and write requests get different treatment. Classify from the user's **opening message**, before doing anything else.

**Read-only** — the deliverable is an answer. Nothing in the repository changes.

> explain, describe, summarise, review, audit, assess, find, search, locate, trace, compare, diagnose, "why does…", "where is…", "how does…", "is there a…", "what happens when…"

**Write** — the deliverable is a change. A file is edited, created, deleted, generated, committed, deployed, or migrated.

> fix, add, change, implement, refactor, rename, remove, upgrade, migrate, generate, write, build, deploy, "make it…", "can you update…"

Rules for classifying:

- **Ambiguity means write.** "Look at the login bug" is read-only; "look at the login bug and sort it" is write. If you cannot tell which one you have, treat it as a write and ask.
- **"Fix" is a write**, even when the fix turns out to be one character.
- **A read-only request that becomes a write mid-session asks the question at that moment**, before the first edit — not at the start, and not after.
- **A read-only task never edits anything**, including a file it created for its own convenience. Use a scratch directory outside the repository.

---

## 2. Read-only: do not ask. State and proceed.

There is nothing to decide. The working copy is what the user is asking about, and switching branches under them would change the answer.

**Say one line, then start.** No question, no options, no waiting.

```
Read-only request, so using the local working copy as it stands.
FACT: on feature/rate-limits, 0 behind / 2 ahead of origin/develop.
```

Add a warning line **only** when something could make the answer wrong:

```
Read-only request, so using the local working copy as it stands.
WARNING: this branch is 5 commits behind origin/develop — findings may already be fixed upstream.
```

```
Read-only request, so using the local working copy as it stands.
WARNING: 3 uncommitted files in the tree, so this is not what is on any branch.
```

Rules:

- Warn when the branch is **behind** the base, and say what that costs: a finding may already be fixed upstream.
- Warn when the tree has **uncommitted changes**, and say what that costs: you are reading something that exists nowhere else.
- Say nothing extra when the branch is current and the tree is clean. One state line is enough.
- **Do not offer to update the branch.** The user asked a question about this tree. If the staleness turns out to matter for a specific finding, say so on that finding.

---

## 3. Write: ask through the interface's question control

A write needs a decision only the user can make, so ask — but **ask it as a structured question with selectable options, not as a block of text in your reply.**

- In Claude Code, use the `AskUserQuestion` tool.
- In any harness with an equivalent structured-choice control, use that.
- **Only where the harness has no such control** do you print the options as text and wait for a number.

**Never print the numbered list as prose when a question control is available.** A text list the user has to answer by typing a digit is worse in every way: it scrolls away, it is easy to answer ambiguously, and it does not show the user that the session is blocked on them.

### The question

- **Header:** `Working tree`
- **Question:** `What working tree? <branch> is <N> commits behind <base branch>.`
- **Options**, in this fixed order, so the answer is one click:

| # | Label | What it means |
|---|---|---|
| 1 | New branch from latest `<base>` | `git fetch origin <base> && git checkout -b <work branch> origin/<base>` |
| 2 | Pull latest `<base>` and work here | `git pull --ff-only` on the current branch |
| 3 | Work on the existing files as they are | Change nothing about the branch. State the behind-count once and carry on. |
| 4 | New work tree from latest `<base>` | `git worktree add <path> -b <work branch> origin/<base>`, then work in that path |
| 5 | Other | The user names a branch, a ref, or a different arrangement. |

Rules for the question:

- Ask it **once**, at the start of the task. Do not re-ask it every turn.
- Keep the order fixed. A user who has seen it before should be able to answer without reading it.
- Fill `<branch>`, `<N>` and `<base branch>` with the measured values. If the branch is current, say `0 commits behind`.
- **Wait for the answer.** Do not pick a default and continue.
- **Uncommitted changes are a second question, asked in the same message.** Name the files. A modified file that is not a generated artifact belongs to somebody, and absorbing it into your change is how it gets lost.

### When an option fails

An option that fails is not an answer. `git pull --ff-only` refuses on a diverged branch; `git checkout -b` fails on a name that already exists.

Print the exact error, print `git log --oneline origin/<base>..HEAD`, and **ask again**. Never choose a merge, a rebase or a reset yourself to make the option work.

---

## 4. Never change the tree without being told

**Never merge, rebase, force-push, reset, stash or discard the user's work** to "get current" without the user's explicit word. Fetching and reporting is always safe. Changing the working tree is not.

If the user picks option 3 on a stale branch, that is their decision: state the behind-count in one line and continue. Do not raise it again.

---

## 5. Why

- Work built on a stale base collides at merge time, and the collision surfaces long after the reasoning that produced the code is gone.
- Audit and review output is worse: every finding is precise, anchored, and already fixed upstream. Nothing downstream catches it, because a skeptic pass reading the same stale tree confirms the finding honestly. On that tree it *is* true. **This is exactly why a read-only task still gets the warning line** — it does not need a decision, it needs the reader to know what the findings are anchored to.
- A single merged pull request on the file you are working in is enough to invalidate the whole task. "Only a bit behind" is not a pass.
- And the reason for not asking on a read-only request: a question the user cannot get wrong is a question that should not have been asked. It costs a turn, it interrupts, and every unnecessary one makes the necessary one easier to click through without reading.

---

## 6. Report line

State the base and the freshness in the first message of the task, in one line:

`FACT: on <branch>, 0 behind / 3 ahead of origin/<base>.`

An audit or review report that does not name the ref it was checked against cannot be acted on — the reader has no way to tell whether the findings still exist.
