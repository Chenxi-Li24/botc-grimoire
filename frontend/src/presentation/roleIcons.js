import iconIds from './role-icon-ids.json'

const availableIcons = new Set(iconIds)

export function roleIconUrl(roleId) {
  return availableIcons.has(roleId) ? `/role-icons/${roleId}.webp` : null
}
