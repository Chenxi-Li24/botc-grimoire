export function resolveEntry({ hash, session }) {
  if (hash.startsWith('#/storyteller-preview')) {
    return { redirectHash: '#/storyteller', vuePageAfterRedirect: 'storyteller' }
  }

  if (hash.startsWith('#/storyteller')) {
    return { vuePage: 'storyteller' }
  }

  if (hash.startsWith('#/account')) return { vuePage: 'account' }
  if (hash.startsWith('#/history')) return { vuePage: 'history' }
  return { vuePage: session?.player_id ? 'player' : 'join' }
}
