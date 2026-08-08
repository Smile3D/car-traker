import type { Receipt } from '~/types/receipts'
import type { ApiError } from '~/composables/useApi'

export interface ReceiptUploadOptions {
    description?: string
    serviceRecordId?: number
    fuelRefillId?: number
}

export const useReceiptStore = defineStore('receipt', () => {
    const receipts = ref<Receipt[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiDelete, apiGetBlob } = useApi()

    const fetchReceipts = async (carId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            receipts.value = await apiGet<Receipt[]>(`/cars/${carId}/receipts`)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const uploadReceipt = async (carId: number, file: File, options: ReceiptUploadOptions = {}): Promise<Receipt> => {
        isLoading.value = true
        error.value = null
        try {
            const formData = new FormData()
            formData.append('file', file)
            if (options.description) {
                formData.append('description', options.description)
            }
            if (options.serviceRecordId !== undefined) {
                formData.append('service_record_id', String(options.serviceRecordId))
            }
            if (options.fuelRefillId !== undefined) {
                formData.append('fuel_refill_id', String(options.fuelRefillId))
            }

            const createdReceipt = await apiPost<Receipt>(`/cars/${carId}/receipts`, formData)
            receipts.value.unshift(createdReceipt)
            return createdReceipt
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteReceipt = async (carId: number, receiptId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/cars/${carId}/receipts/${receiptId}`)
            receipts.value = receipts.value.filter((receipt) => receipt.id !== receiptId)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const fetchReceiptImageUrl = async (carId: number, receiptId: number): Promise<string> => {
        const imageBlob = await apiGetBlob(`/cars/${carId}/receipts/${receiptId}/file`)
        return URL.createObjectURL(imageBlob)
    }

    return {
        receipts,
        isLoading,
        error,
        fetchReceipts,
        uploadReceipt,
        deleteReceipt,
        fetchReceiptImageUrl
    }
})
