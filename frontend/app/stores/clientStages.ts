import type { ClientStage, ClientStageCreateInput, ClientStageUpdateInput } from '~/types/clients'
import type { ApiError } from '~/composables/useApi'

export const useClientStageStore = defineStore('clientStage', () => {
    const stages = ref<ClientStage[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    // Fetches BOTH seller and buyer stage sets and merges them into one
    // list. stages.value is the single source of truth for both Kanban
    // boards — filtering by client_type happens locally (mirroring the
    // full-list pattern used by clientStore/listingStore), never via a
    // single-type fetch that would overwrite the merged list with a subset.
    const fetchStages = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            const [sellerStages, buyerStages] = await Promise.all([
                apiGet<ClientStage[]>('/client-stages?client_type=seller'),
                apiGet<ClientStage[]>('/client-stages?client_type=buyer')
            ])
            stages.value = [...sellerStages, ...buyerStages]
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const createStage = async (stageInput: ClientStageCreateInput): Promise<ClientStage> => {
        isLoading.value = true
        error.value = null
        try {
            const createdStage = await apiPost<ClientStage>('/client-stages', stageInput)
            stages.value.push(createdStage)
            return createdStage
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const renameStage = async (stageId: number, stageInput: ClientStageUpdateInput): Promise<ClientStage> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedStage = await apiPatch<ClientStage>(`/client-stages/${stageId}`, stageInput)
            stages.value = stages.value.map((stage) => stage.id === stageId ? updatedStage : stage)
            return updatedStage
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const reorderStages = async (stageIds: number[]): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            const reorderedStages = await apiPatch<ClientStage[]>('/client-stages/reorder', { stage_ids: stageIds })
            const reorderedById = new Map(reorderedStages.map((stage) => [stage.id, stage]))
            stages.value = stages.value.map((stage) => reorderedById.get(stage.id) ?? stage)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteStage = async (stageId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/client-stages/${stageId}`)
            stages.value = stages.value.filter((stage) => stage.id !== stageId)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        stages,
        isLoading,
        error,
        fetchStages,
        createStage,
        renameStage,
        reorderStages,
        deleteStage
    }
})
