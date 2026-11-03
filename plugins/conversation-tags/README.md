# conversation-tags

Lose track of which Claude conversation is waiting on you? This plugin puts a status badge on the conversation title in the Claude desktop app sidebar, and lists every tagged conversation from any session.

## Install

```
/plugin install conversation-tags --marketplace paulmorrishill/ClaudeAnnoyanceReduction
```

## Use

| Command | Sidebar title |
|---|---|
| `/tag waiting review the PR body` | `🟡 Original title` |
| `/tag blocked` | `🔴 Original title` |
| `/tag 🐛 flaky e2e` | `🐛 Original title` (a label that starts with an emoji is used as typed) |
| `/tag release-prep` | `[release-prep] Original title` |
| `/untag` | `Original title` |
| `/tags` | Lists every tagged conversation: badge, title, label, note, time, folder. |

Words that become an emoji: `waiting` / `waiting-on-you` / `needs-you` 🟡, `blocked` / `stuck` 🔴, `done` / `merged` ✅, `issue-sent` / `sent` 📨, `review` / `in-review` 👀, `wip` / `in-progress` 🔧, `todo` / `later` 📌, `deploying` 🚀, `testing` 🧪, `idea` 💡.

Claude gets the same through three tools: `set_tag`, `clear_tag` and `list_tags`. Tell a skill to call `set_tag` at the end of a turn that leaves work for you (for example a drafted issue you have not approved), and `clear_tag` when nothing is left.

## How it works

- Claude Code plugins cannot draw inside the desktop sidebar. The only per-conversation thing a plugin can change there is the title, so the badge is a title prefix, written through the desktop app's own session tools.
- When the tag changes, the plugin removes the badge it wrote before and writes the new one. If you rename a conversation by hand while it has a badge, the old badge can stay.
- Tags are kept in the plugin's own store, shared by all sessions on the machine.
- Outside the desktop app (the terminal CLI) the tag is still stored and listed by `/tags`; no title changes.
