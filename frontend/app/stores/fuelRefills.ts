import type { FuelRefill, FuelRefillCreateInput, FuelRefillUpdateInput } from '~/types/fuelRefills'
import type { ApiError } from '~/composables/useApi'

export const useFuelRefillStore = defineStore('fuelRefill', () => {
    const fuelRefills = ref<FuelRefill[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    const fetchFuelRefills = async (carId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            fuelRefills.value = await apiGet<FuelRefill[]>(`/cars/${carId}/fuel-refills`)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const createFuelRefill = async (carId: number, refillInput: FuelRefillCreateInput): Promise<FuelRefill> => {
        isLoading.value = true
        error.value = null
        try {
            const createdFuelRefill = await apiPost<FuelRefill>(`/cars/${carId}/fuel-refills`, refillInput)
            fuelRefills.value.push(createdFuelRefill)
            return createdFuelRefill
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateFuelRefill = async (carId: number, refillId: number, refillInput: FuelRefillUpdateInput): Promise<FuelRefill> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedFuelRefill = await apiPatch<FuelRefill>(`/cars/${carId}/fuel-refills/${refillId}`, refillInput)
            fuelRefills.value = fuelRefills.value.map((refill) => refill.id === refillId ? updatedFuelRefill : refill)
            return updatedFuelRefill
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteFuelRefill = async (carId: number, refillId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/cars/${carId}/fuel-refills/${refillId}`)
            fuelRefills.value = fuelRefills.value.filter((refill) => refill.id !== refillId)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    return {
        fuelRefills,
        isLoading,
        error,
        fetchFuelRefills,
        createFuelRefill,
        updateFuelRefill,
        deleteFuelRefill
    }
})
