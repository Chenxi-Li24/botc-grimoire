export async function resolveEntry({ hash, playerId, validatePlayer }) {
  if (hash.startsWith('#/storyteller-preview')) {
    return { redirectHash: '#/storyteller', vuePageAfterRedirect: 'storyteller' }
  }

  if (hash.startsWith('#/storyteller')) {
    return { vuePage: 'storyteller' }
  }

  if (!playerId) return 'join'

  try {
    await validatePlayer(playerId)
    return { vuePage: 'player' }
  } catch {
    return 'join'
  }
}
