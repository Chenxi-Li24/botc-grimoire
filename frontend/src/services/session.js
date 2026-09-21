import { ST_PASSWORD_KEY } from '../constants.js'

let csrfToken = null
export const getCsrfToken = () => csrfToken
export const setCsrfToken = (token) => { csrfToken = token || null }
export const clearCsrfToken = () => { csrfToken = null }
export const getStorytellerPassword = () => localStorage.getItem(ST_PASSWORD_KEY)
export const setStorytellerPassword = (password) => localStorage.setItem(ST_PASSWORD_KEY, password)
export const clearStorytellerPassword = () => localStorage.removeItem(ST_PASSWORD_KEY)
