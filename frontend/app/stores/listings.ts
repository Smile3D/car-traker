import type { Listing, ListingFormInput, MarkListingOnServiceInput, MarkListingSoldInput } from '~/types/listings'
import type { ApiError } from '~/composables/useApi'

export const useListingStore = defineStore('listing', () => {
    const listings = ref<Listing[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    // Always fetches the COMPLETE list. listingStore.listings is the single
    // source of truth for every consumer (dashboard, analytics, inventory) —
    // any status filtering (e.g. on the inventory page) must happen locally
    // over this full list, never via a separate filtered server request.
    const fetchListings = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            listings.value = await apiGet<Listing[]>('/listings')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const fetchListingById = async (listingId: number): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const fetchedListing = await apiGet<Listing>(`/listings/${listingId}`)
            const existingIndex = listings.value.findIndex((listing) => listing.id === listingId)
            if (existingIndex === -1) {
                listings.value.push(fetchedListing)
            } else {
                listings.value[existingIndex] = fetchedListing
            }
            return fetchedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const createListing = async (listingInput: ListingFormInput): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const createdListing = await apiPost<Listing>('/listings', listingInput)
            listings.value.push(createdListing)
            return createdListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateListing = async (listingId: number, listingInput: ListingFormInput): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedListing = await apiPatch<Listing>(`/listings/${listingId}`, listingInput)
            listings.value = listings.value.map((listing) => listing.id === listingId ? updatedListing : listing)
            return updatedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteListing = async (listingId: number, reason?: string): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/listings/${listingId}`, reason ? { reason } : undefined)
            listings.value = listings.value.filter((listing) => listing.id !== listingId)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const markListingSold = async (listingId: number, markSoldInput: MarkListingSoldInput): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedListing = await apiPost<Listing>(`/listings/${listingId}/mark-sold`, markSoldInput)
            listings.value = listings.value.map((listing) => listing.id === listingId ? updatedListing : listing)
            return updatedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const markListingOnService = async (listingId: number, markOnServiceInput: MarkListingOnServiceInput): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedListing = await apiPost<Listing>(`/listings/${listingId}/mark-on-service`, markOnServiceInput)
            listings.value = listings.value.map((listing) => listing.id === listingId ? updatedListing : listing)
            return updatedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const returnListingToWork = async (listingId: number): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedListing = await apiPost<Listing>(`/listings/${listingId}/return-to-work`)
            listings.value = listings.value.map((listing) => listing.id === listingId ? updatedListing : listing)
            return updatedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    // A plain status-only PATCH — bypasses updateListing's full ListingFormInput
    // requirement, same reasoning as returnListingToWork above. The backend
    // requires a buyer Client to already exist for this listing before it'll
    // accept the transition into "reserved" (see routers/listings.py).
    const reserveListing = async (listingId: number): Promise<Listing> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedListing = await apiPatch<Listing>(`/listings/${listingId}`, { status: 'reserved' })
            listings.value = listings.value.map((listing) => listing.id === listingId ? updatedListing : listing)
            return updatedListing
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const bulkDeleteListings = async (listingIds: number[]): Promise<{ deletedCount: number, skippedMessages: string[] }> => {
        isLoading.value = true
        error.value = null
        try {
            const result = await apiPost<{ deleted_count: number, deleted_ids: number[], skipped: string[] }>('/listings/bulk-delete', { ids: listingIds })
            const deletedIds = new Set(result.deleted_ids)
            listings.value = listings.value.filter((listing) => !deletedIds.has(listing.id))
            return { deletedCount: result.deleted_count, skippedMessages: result.skipped }
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        listings,
        isLoading,
        error,
        fetchListings,
        fetchListingById,
        createListing,
        updateListing,
        deleteListing,
        markListingSold,
        markListingOnService,
        returnListingToWork,
        reserveListing,
        bulkDeleteListings
    }
})
