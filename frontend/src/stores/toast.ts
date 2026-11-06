import { defineStore } from 'pinia'
import { toast } from 'vue-sonner'

/** Short, non-blocking notifications (replaces window.alert). A thin wrapper over vue-sonner. */
export const useToastStore = defineStore('toast', () => {
  const info = (message: string, durationMs = 5000) => toast.info(message, { duration: durationMs })
  const success = (message: string, durationMs = 5000) => toast.success(message, { duration: durationMs })
  const error = (message: string, durationMs = 6000) => toast.error(message, { duration: durationMs })

  return { info, success, error }
})
