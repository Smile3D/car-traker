import type { ApiError } from '~/composables/useApi'

export const useCarDataStore = defineStore('carData', () => {
    const makes = ref<string[]>([])
    const modelsByMake = ref<Record<string, string[]>>({})
    const isLoadingMakes = ref(false)
    const isLoadingModels = ref(false)
    const error = ref<string | null>(null)

    const { apiGet } = useApi()

    const fetchMakes = async (): Promise<void> => {
        if (makes.value.length > 0) {
            return
        }

        isLoadingMakes.value = true
        error.value = null
        try {
            makes.value = await apiGet<string[]>('/car-data/makes')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoadingMakes.value = false
        }
    }

    const fetchModelsForMake = async (make: string): Promise<void> => {
        if (!make || modelsByMake.value[make]) {
            return
        }

        isLoadingModels.value = true
        error.value = null
        try {
            const fetchedModels = await apiGet<string[]>(`/car-data/models?make=${encodeURIComponent(make)}`)
            modelsByMake.value = { ...modelsByMake.value, [make]: fetchedModels }
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoadingModels.value = false
        }
    }

    return {
        makes,
        modelsByMake,
        isLoadingMakes,
        isLoadingModels,
        error,
        fetchMakes,
        fetchModelsForMake
    }
})
