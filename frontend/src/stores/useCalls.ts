import { create } from 'zustand'
import { getCallLogs, getCallStats, retryCall, closeCall } from '../lib/endpoints'
import type { CallLog, CallStats } from '../lib/schemas'

type CallsState = {
  logs: CallLog[]
  stats?: CallStats
  loading: boolean
  loaded: boolean
  error?: string
  load: () => Promise<void>
  retry: (logId: string) => Promise<void>
  close: (logId: string) => Promise<void>
}

export const useCalls = create<CallsState>((set, get) => ({
  logs: [],
  loading: false,
  loaded: false,
  load: async () => {
    set({ loading: true, error: undefined })
    try {
      const [logs, stats] = await Promise.all([getCallLogs(), getCallStats()])
      set({ logs, stats, loading: false, loaded: true })
    } catch (e) {
      set({ loading: false, loaded: true, error: (e as Error).message })
    }
  },
  retry: async (logId) => {
    await retryCall(logId)
    await get().load()
  },
  close: async (logId) => {
    await closeCall(logId)
    await get().load()
  },
}))
