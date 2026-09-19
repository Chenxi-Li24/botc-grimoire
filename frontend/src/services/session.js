import { PLAYER_ID_KEY, ST_PASSWORD_KEY } from '../constants.js'

export const getPlayerId = () => localStorage.getItem(PLAYER_ID_KEY)
export const setPlayerId = (id) => localStorage.setItem(PLAYER_ID_KEY, id)
export const clearPlayerId = () => localStorage.removeItem(PLAYER_ID_KEY)
export const getStorytellerPassword = () => localStorage.getItem(ST_PASSWORD_KEY)
export const setStorytellerPassword = (password) => localStorage.setItem(ST_PASSWORD_KEY, password)
export const clearStorytellerPassword = () => localStorage.removeItem(ST_PASSWORD_KEY)
