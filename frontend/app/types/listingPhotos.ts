export interface ListingPhoto {
    id: number
    listing_id: number
    order: number
    uploaded_at: string
}

export interface ListingPhotoReorderInput {
    photo_ids: number[]
}

export interface ListingPhotoUploadResult {
    created: ListingPhoto[]
    errors: string[]
}
