import { PLAYER_ID_KEY } from '../constants.js'

export const getPlayerId = () => localStorage.getItem(PLAYER_ID_KEY)
export const setPlayerId = (id) => localStorage.setItem(PLAYER_ID_KEY, id)
export const clearPlayerId = () => localStorage.removeItem(PLAYER_ID_KEY)
