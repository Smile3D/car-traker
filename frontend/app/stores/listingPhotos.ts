import type { ListingPhoto, ListingPhotoUploadResult } from '~/types/listingPhotos'
import type { ApiError } from '~/composables/useApi'

// Scoped to whichever single listing's gallery is currently being managed
// (the listing detail page), mirroring how receiptStore is scoped to
// whichever single car's receipts are being viewed — never holds photos for
// more than one listing at a time.
export const useListingPhotoStore = defineStore('listingPhoto', () => {
    const photos = ref<ListingPhoto[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete, apiGetBlob } = useApi()

    const fetchPhotos = async (listingId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            photos.value = await apiGet<ListingPhoto[]>(`/listings/${listingId}/photos`)
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const uploadPhotos = async (listingId: number, files: File[]): Promise<ListingPhotoUploadResult> => {
        isLoading.value = true
        error.value = null
        try {
            const formData = new FormData()
            for (const file of files) {
                formData.append('files', file)
            }

            const result = await apiPost<ListingPhotoUploadResult>(`/listings/${listingId}/photos`, formData)
            photos.value.push(...result.created)
            return result
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deletePhoto = async (listingId: number, photoId: number): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/listings/${listingId}/photos/${photoId}`)
            photos.value = photos.value.filter((photo) => photo.id !== photoId)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const reorderPhotos = async (listingId: number, photoIds: number[]): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            const reorderedPhotos = await apiPatch<ListingPhoto[]>(`/listings/${listingId}/photos/reorder`, { photo_ids: photoIds })
            const reorderedById = new Map(reorderedPhotos.map((photo) => [photo.id, photo]))
            photos.value = photos.value.map((photo) => reorderedById.get(photo.id) ?? photo)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const fetchPhotoImageUrl = async (listingId: number, photoId: number): Promise<string> => {
        const imageBlob = await apiGetBlob(`/listings/${listingId}/photos/${photoId}/file`)
        return URL.createObjectURL(imageBlob)
    }

    return {
        photos,
        isLoading,
        error,
        fetchPhotos,
        uploadPhotos,
        deletePhoto,
        reorderPhotos,
        fetchPhotoImageUrl
    }
})
