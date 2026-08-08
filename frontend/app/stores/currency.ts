import type { CurrencyRate, CurrencySettingsUpdateInput } from '~/types/currency'
import type { ApiError } from '~/composables/useApi'

// A currency reference value is informational only — nothing in the system
// converts or stores amounts in USD. Fetched once per session (not on every
// component render/mount) and cached here; hasFetched flips true regardless
// of outcome so a 403 (individual account, no company) or a transient
// failure doesn't retry on every page navigation.
export const useCurrencyStore = defineStore('currency', () => {
    const rate = ref<CurrencyRate | null>(null)
    const isLoading = ref(false)
    const error = ref<string | null>(null)
    const hasFetched = ref(false)

    const { apiGet, apiPatch } = useApi()

    const fetchRate = async (): Promise<void> => {
        if (hasFetched.value) {
            return
        }

        isLoading.value = true
        error.value = null
        try {
            rate.value = await apiGet<CurrencyRate>('/currency/rate')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            hasFetched.value = true
            isLoading.value = false
        }
    }

    const updateSettings = async (settingsUpdate: CurrencySettingsUpdateInput): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            rate.value = await apiPatch<CurrencyRate>('/company/currency-settings', settingsUpdate)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        rate,
        isLoading,
        error,
        fetchRate,
        updateSettings
    }
})
