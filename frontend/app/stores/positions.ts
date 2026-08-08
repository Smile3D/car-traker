import type { Position, PositionCreateInput, PositionUpdateInput } from '~/types/positions'
import type { ApiError } from '~/composables/useApi'

export const usePositionStore = defineStore('position', () => {
    const positions = ref<Position[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    const fetchPositions = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            positions.value = await apiGet<Position[]>('/positions')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const createPosition = async (positionInput: PositionCreateInput): Promise<Position> => {
        isLoading.value = true
        error.value = null
        try {
            const createdPosition = await apiPost<Position>('/positions', positionInput)
            positions.value.push(createdPosition)
            return createdPosition
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const renamePosition = async (positionId: number, positionInput: PositionUpdateInput): Promise<Position> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedPosition = await apiPatch<Position>(`/positions/${positionId}`, positionInput)
            positions.value = positions.value.map((position) => position.id === positionId ? updatedPosition : position)
            return updatedPosition
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deletePosition = async (positionId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/positions/${positionId}`)
            positions.value = positions.value.filter((position) => position.id !== positionId)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        positions,
        isLoading,
        error,
        fetchPositions,
        createPosition,
        renamePosition,
        deletePosition
    }
})
