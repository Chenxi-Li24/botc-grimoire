export type Team = 'townsfolk' | 'outsider' | 'minion' | 'demon'

export interface Role {
  id: string
  name: string
  en: string
  team: Team
  ability: string
}

export interface PublicPlayer {
  id: string
  name: string
  seat: number
  alive: boolean
}

export interface PlayerView {
  status: 'lobby' | 'playing'
  me: PublicPlayer & { role?: Role }
  players: PublicPlayer[]
}

export interface StorytellerView {
  status: 'lobby' | 'playing'
  script: string
  players: (PublicPlayer & { role?: Role })[]
  roles: Role[]
}
