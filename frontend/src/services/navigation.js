export async function resolveEntry({ hash, playerId, validatePlayer }) {
  if (hash.startsWith('#/storyteller')) {
    return { legacyUrl: `/legacy/${hash}` }
  }

  if (!playerId) return 'join'

  try {
    await validatePlayer(playerId)
    return { legacyUrl: '/legacy/' }
  } catch {
    return 'join'
  }
}

export function goToLegacy(url) {
  window.location.replace(url)
}
