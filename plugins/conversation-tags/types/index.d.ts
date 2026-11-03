export type Tag = {
  label: string
  note: string
  cwd: string
  updatedAt: number
  // The prefix written on the session title, kept so the next change strips it exactly.
  badge?: string
  // The sidebar title without the badge, so /tags names the conversation.
  title?: string
}

declare module 'claude-code' {
  interface PluginState {
    'conversation-tags': { current: Tag | null }
  }
}
