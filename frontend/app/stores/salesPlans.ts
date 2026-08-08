import type { SalesPlanProgress, SalesPlanUpsertInput } from '~/types/salesPlans'
import type { ApiError } from '~/composables/useApi'

export const useSalesPlanStore = defineStore('salesPlan', () => {
    const plans = ref<SalesPlanProgress[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiDelete } = useApi()

    const fetchSalesPlans = async (month: string): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            plans.value = await apiGet<SalesPlanProgress[]>(`/sales-plans?month=${month}`)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    // Doesn't patch `plans` locally — upserting one employee's target also
    // changes the company-total row's sum, and that aggregation is computed
    // server-side only (never re-derived in the frontend), so the caller
    // re-fetches the whole month afterwards instead.
    const upsertSalesPlan = async (input: SalesPlanUpsertInput): Promise<SalesPlanProgress> => {
        isLoading.value = true
        error.value = null
        try {
            return await apiPost<SalesPlanProgress>('/sales-plans', input)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteSalesPlan = async (planId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/sales-plans/${planId}`)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        plans,
        isLoading,
        error,
        fetchSalesPlans,
        upsertSalesPlan,
        deleteSalesPlan
    }
})
