import { create } from 'zustand'
import { getJobPosts } from '../lib/endpoints'
import type { JobPost } from '../lib/schemas'

type JobsState = {
  jobs: JobPost[]
  loading: boolean
  error?: string
  load: () => Promise<void>
}

export const useJobs = create<JobsState>((set) => ({
  jobs: [],
  loading: false,
  load: async () => {
    set({ loading: true, error: undefined })
    try {
      set({ jobs: await getJobPosts(), loading: false })
    } catch (e) {
      set({ loading: false, error: (e as Error).message })
    }
  },
}))
