import type { DealHistoryEntry } from '~/types/dealHistory'
import type { ApiError } from '~/composables/useApi'

// Always fetches the COMPLETE company log — search/type/date filtering on
// the deal-history page all happen locally over this list, same convention
// as listingStore/clientStore. The backend also accepts deal_type/
// employee_id/search query params (useful for a future per-employee stats
// view), just not exercised by this page yet.
export const useDealHistoryStore = defineStore('dealHistory', () => {
    const entries = ref<DealHistoryEntry[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet } = useApi()

    const fetchDealHistory = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            entries.value = await apiGet<DealHistoryEntry[]>('/deal-history')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    return {
        entries,
        isLoading,
        error,
        fetchDealHistory
    }
})
