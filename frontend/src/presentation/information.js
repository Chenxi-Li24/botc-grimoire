export function formatInformationResult(result, roles = []) {
  if (result == null) return '暂无信息'
  if (typeof result === 'string' || typeof result === 'number') return String(result)
  if (typeof result === 'object' && !Array.isArray(result)
      && 'character_id' in result && Array.isArray(result.seats)) {
    if (!result.character_id || !result.seats.length) return '没有对应角色在场'
    const role = roles.find((item) => item.id === result.character_id)
    const seats = result.seats.map((seat) => `${seat}号`).join('与')
    return `${seats}中有一位是${role?.name || result.character_id}`
  }
  return JSON.stringify(result)
}
