import type { ServiceRecord, ServiceRecordCreateInput, ServiceRecordUpdateInput } from '~/types/serviceRecords'
import type { ApiError } from '~/composables/useApi'

export const useServiceRecordStore = defineStore('serviceRecord', () => {
    const serviceRecords = ref<ServiceRecord[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    const fetchServiceRecords = async (carId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            serviceRecords.value = await apiGet<ServiceRecord[]>(`/cars/${carId}/service-records`)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const createServiceRecord = async (carId: number, recordInput: ServiceRecordCreateInput): Promise<ServiceRecord> => {
        isLoading.value = true
        error.value = null
        try {
            const createdServiceRecord = await apiPost<ServiceRecord>(`/cars/${carId}/service-records`, recordInput)
            serviceRecords.value.push(createdServiceRecord)
            return createdServiceRecord
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateServiceRecord = async (carId: number, recordId: number, recordInput: ServiceRecordUpdateInput): Promise<ServiceRecord> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedServiceRecord = await apiPatch<ServiceRecord>(`/cars/${carId}/service-records/${recordId}`, recordInput)
            serviceRecords.value = serviceRecords.value.map((record) => record.id === recordId ? updatedServiceRecord : record)
            return updatedServiceRecord
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteServiceRecord = async (carId: number, recordId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/cars/${carId}/service-records/${recordId}`)
            serviceRecords.value = serviceRecords.value.filter((record) => record.id !== recordId)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    return {
        serviceRecords,
        isLoading,
        error,
        fetchServiceRecords,
        createServiceRecord,
        updateServiceRecord,
        deleteServiceRecord
    }
})
