import { create } from 'zustand'
import { getCandidates } from '../lib/endpoints'
import type { Candidate } from '../lib/schemas'

type CandidatesState = {
  candidates: Candidate[]
  loading: boolean
  loaded: boolean
  error?: string
  load: () => Promise<void>
}

export const useCandidates = create<CandidatesState>((set) => ({
  candidates: [],
  loading: false,
  loaded: false,
  load: async () => {
    set({ loading: true, error: undefined })
    try {
      set({ candidates: await getCandidates(), loading: false, loaded: true })
    } catch (e) {
      set({ loading: false, loaded: true, error: (e as Error).message })
    }
  },
}))
