import type { ArchiveCleanupSchedule } from '~/types/archive'
import type { ApiError } from '~/composables/useApi'

// One shared value for the whole archive (not per-listing) — fetched once
// per session and cached, mirroring useCurrencyStore's pattern for the same
// kind of "informational, rarely-changing, single global value" data.
export const useArchiveCleanupScheduleStore = defineStore('archiveCleanupSchedule', () => {
    const schedule = ref<ArchiveCleanupSchedule | null>(null)
    const isLoading = ref(false)
    const error = ref<string | null>(null)
    const hasFetched = ref(false)

    const { apiGet } = useApi()

    const fetchSchedule = async (): Promise<void> => {
        if (hasFetched.value) {
            return
        }

        isLoading.value = true
        error.value = null
        try {
            schedule.value = await apiGet<ArchiveCleanupSchedule>('/crm/archive/cleanup-schedule')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            hasFetched.value = true
            isLoading.value = false
        }
    }

    return {
        schedule,
        isLoading,
        error,
        fetchSchedule
    }
})
