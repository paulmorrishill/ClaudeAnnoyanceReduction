import { atom, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Tag } from '../types'

// All sessions share one $.store file, so the index below is cross-session.
const INDEX = 'tags'
const current = atom({ plugin: 'conversation-tags', key: 'current' } as const, null)

type Index = Record<string, Tag>

const loadIndex = async ($: EngineInterface): Promise<Index> =>
  ((await $.store.get(INDEX)) as Index | undefined) ?? {}

// The desktop sidebar draws no plugin content, so the badge is a prefix on the
// session title. A label that starts with an emoji is the badge as typed; a
// known word becomes its emoji; any other label shows as "[label]".
const EMOJI = /^\p{Extended_Pictographic}/u
const KNOWN: Record<string, string> = {
  'waiting': '🟡', 'waiting-on-you': '🟡', 'waiting-on-me': '🟡', 'needs-you': '🟡',
  'blocked': '🔴', 'stuck': '🔴',
  'done': '✅', 'merged': '✅',
  'issue-sent': '📨', 'sent': '📨',
  'review': '👀', 'in-review': '👀',
  'wip': '🔧', 'in-progress': '🔧',
  'todo': '📌', 'later': '📌',
  'deploying': '🚀', 'testing': '🧪', 'idea': '💡',
}

const badgeFor = (label: string) =>
  EMOJI.test(label) ? label : KNOWN[label.toLowerCase()] ?? `[${label}]`

const sessionTitle = async ($: EngineInterface) => {
  const got = await $.tool.call({ tool: 'mcp__ccd_session_mgmt__get_session', session_id: 'self' })
  return String((JSON.parse(got.text ?? '{}') as { title?: string }).title ?? '')
}

// Strips the old badge (if the title still starts with it) and writes the new one.
// Returns the title without any badge, or undefined outside the desktop app.
const showInSidebar = async ($: EngineInterface, oldBadge: string | undefined, badge: string | null) => {
  try {
    const title = await sessionTitle($)
    const bare = oldBadge && title.startsWith(`${oldBadge} `) ? title.slice(oldBadge.length + 1) : title
    const next = badge === null ? bare : `${badge} ${bare}`.trim()
    if (next !== title) {
      await $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: 'self', title: next })
    }
    return bare
  } catch {
    // No desktop app here: the tag still lives in the store and in /tags.
    return undefined
  }
}

const setTag = async ($: EngineInterface, label: string, note: string) => {
  const sessionId = await $.session.id()
  const index = await loadIndex($)
  const badge = badgeFor(label)
  const tag: Tag = { label, note, badge, cwd: await $.session.cwd(), updatedAt: await $.clock.now() }
  tag.title = await showInSidebar($, index[sessionId]?.badge, badge)
  await $.store.set(INDEX, { ...(await loadIndex($)), [sessionId]: tag })
  await update($, current, () => tag)
  return tag
}

const clearTag = async ($: EngineInterface) => {
  const sessionId = await $.session.id()
  const { [sessionId]: old, ...rest } = await loadIndex($)
  await $.store.set(INDEX, rest)
  await update($, current, () => null)
  await showInSidebar($, old?.badge, null)
}

const listText = (index: Index, self: string) => {
  const rows = Object.entries(index).sort((a, b) => b[1].updatedAt - a[1].updatedAt)
  if (rows.length === 0) return 'No tagged conversations.'
  return rows
    .map(([id, t]) => {
      const when = new Date(t.updatedAt).toISOString().slice(0, 16).replace('T', ' ')
      const mark = id === self ? ' (this one)' : ''
      const name = t.title || `session ${id.slice(0, 8)}`
      return `${t.badge ?? `[${t.label}]`} ${name}${mark}
    ${t.label}: ${t.note || '-'}  (${when}, ${t.cwd})`
    })
    .join('\n')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'tag', description: 'Tag this conversation: /tag <label or emoji> [note]' })
    await $.command.register({ name: 'untag', description: 'Remove the tag from this conversation' })
    await $.command.register({ name: 'tags', description: 'List every tagged conversation' })
    await $.tool.register({
      name: 'set_tag',
      description:
        'Set a short status tag on this conversation so the user can track it from other conversations. ' +
        'Use when the conversation is left in a state the user must act on or return to, for example ' +
        '"waiting-on-you", "issue-sent", "blocked", "in-review", "done". Replaces any earlier tag. ' +
        'The badge shows on the conversation title in the sidebar: these labels become an emoji (waiting 🟡, blocked 🔴, ' +
        'done ✅, issue-sent 📨, review 👀, wip 🔧, todo 📌, deploying 🚀, testing 🧪, idea 💡); a label that starts ' +
        'with an emoji is used as typed.',
      inputSchema: {
        type: 'object',
        properties: {
          label: { type: 'string', description: 'Short label, 1-3 words, or an emoji' },
          note: { type: 'string', description: 'One line: what is open or what the user must do' },
        },
        required: ['label'],
      },
    })
    await $.tool.register({ name: 'clear_tag', description: 'Remove the status tag from this conversation.' })
    await $.tool.register({
      name: 'list_tags',
      description: 'List every tagged conversation across sessions, newest first.',
    })

    const index = await loadIndex($)
    const sessionId = await $.session.id()
    await update($, current, () => index[sessionId] ?? null)
    return next(e)
  })

  on('command.run', { command: 'tag' }, async ($, e) => {
    const [label, ...note] = e.args.trim().split(/\s+/)
    if (!label) return { text: 'Usage: /tag <label> [note]' }
    const tag = await setTag($, label, note.join(' '))
    return { text: `Tagged ${tag.badge} ${tag.note}`.trim() }
  })

  on('command.run', { command: 'untag' }, async $ => {
    await clearTag($)
    return { text: 'Tag removed.' }
  })

  on('command.run', { command: 'tags' }, async $ => ({
    text: listText(await loadIndex($), await $.session.id()),
  }))

  on('tool.call', { tool: 'mcp__conversation-tags__set_tag' }, async ($, e) => {
    const input = e as unknown as { label: string; note?: string }
    const tag = await setTag($, input.label, input.note ?? '')
    return { result: `Tagged ${tag.badge} ${tag.note}`.trim() }
  })

  on('tool.call', { tool: 'mcp__conversation-tags__clear_tag' }, async $ => {
    await clearTag($)
    return { result: 'Tag removed.' }
  })

  on('tool.call', { tool: 'mcp__conversation-tags__list_tags' }, async $ => ({
    result: listText(await loadIndex($), await $.session.id()),
  }))
}
