# Conversation tags

Paste this into your `CLAUDE.md`. It needs the [conversation-tags](../plugins/conversation-tags/) plugin. It makes the agent show, on the conversation title in the desktop sidebar, which conversations wait on you and how each task ended.

---

## Conversation tags (sidebar badge)

The `conversation-tags` plugin shows a badge in front of the conversation title in the desktop sidebar. The badge tells the user, from another conversation, which conversations need them and how each task ended.

- The tools are `mcp__conversation-tags__set_tag` and `mcp__conversation-tags__clear_tag`. They can be deferred: load them with `ToolSearch` (`select:mcp__conversation-tags__set_tag,mcp__conversation-tags__clear_tag`). When the tools do not exist, skip every step in this section and say nothing.
- A skill that sets its own tags follows its own tag rules while it runs. These rules apply to every other conversation.
- Set the tag as the last tool call of the turn, before the closing message. Write a one-line `note` that names the task and the result.
- Use one of these three tags:
  - `label: "waiting"` (🟡): the turn ends with a question to the user, an approval link, or a decision only the user can make. Also set it at the start of a long task the user asked for, and keep it until the task ends.
  - `label: "🟢"`: the task the user asked for is complete and checked.
  - `label: "🔴"`: the task failed, is `BLOCKED:`, or is only partly done. A partly done task is a failure: a red test, a non-2xx response, a failed deploy or a step you skipped makes the tag red.
- A turn that only answers a question or talks, with no task, does not change the tag.
