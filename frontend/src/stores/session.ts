import { create } from 'zustand'
import { API_KEY_KEY } from '../lib/api'

type Theme = 'light' | 'dark'
const THEME_KEY = 'hr_theme'

function applyTheme(t: Theme) {
  document.documentElement.setAttribute('data-theme', t)
}

const initialTheme: Theme = ((): Theme => {
  try {
    const t = localStorage.getItem(THEME_KEY)
    return t === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
})()
applyTheme(initialTheme)

type SessionState = {
  apiKey: string
  theme: Theme
  setApiKey: (k: string) => void
  setTheme: (t: Theme) => void
  toggleTheme: () => void
}

export const useSession = create<SessionState>((set) => ({
  apiKey: (() => {
    try {
      return localStorage.getItem(API_KEY_KEY) || ''
    } catch {
      return ''
    }
  })(),
  theme: initialTheme,
  setApiKey: (k) => {
    try {
      localStorage.setItem(API_KEY_KEY, k)
    } catch {
      /* storage unavailable */
    }
    set({ apiKey: k })
  },
  setTheme: (t) => {
    try {
      localStorage.setItem(THEME_KEY, t)
    } catch {
      /* storage unavailable */
    }
    applyTheme(t)
    set({ theme: t })
  },
  toggleTheme: () =>
    set((s) => {
      const t: Theme = s.theme === 'light' ? 'dark' : 'light'
      try {
        localStorage.setItem(THEME_KEY, t)
      } catch {
        /* storage unavailable */
      }
      applyTheme(t)
      return { theme: t }
    }),
}))
