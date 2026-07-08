import { create } from 'zustand'
import { getRankedCandidates, rerank } from '../lib/endpoints'
import type { RankedCandidate } from '../lib/schemas'

type ShortlistState = {
  jdId?: string
  candidates: RankedCandidate[]
  loading: boolean
  loaded: boolean
  error?: string
  load: (jdId: string) => Promise<void>
  reRank: (weights: { cv: number; interview: number }) => Promise<void>
}

export const useShortlist = create<ShortlistState>((set, get) => ({
  candidates: [],
  loading: false,
  loaded: false,
  load: async (jdId) => {
    set({ loading: true, error: undefined, jdId })
    try {
      set({ candidates: await getRankedCandidates(jdId), loading: false, loaded: true })
    } catch (e) {
      set({ loading: false, loaded: true, error: (e as Error).message })
    }
  },
  reRank: async (weights) => {
    const { jdId } = get()
    if (!jdId) return
    await rerank(jdId, weights)
    await get().load(jdId)
  },
}))
