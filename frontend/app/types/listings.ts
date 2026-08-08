import type { ClientEmployeeSummary } from '~/types/clients'
import type { ClientLeadSource } from '~/utils/clientOptions'
import type { ListingFuelType } from '~/utils/listingOptions'

export type ListingCondition = 'new' | 'used'
export type ListingStatus = 'draft' | 'active' | 'reserved' | 'sold' | 'removed' | 'on_service'

export interface ListingSellerSummary {
    id: number
    employee_id: number | null
    employee: ClientEmployeeSummary | null
}

export interface Listing {
    id: number
    company_id: number
    seller: ListingSellerSummary | null

    brand: string
    model: string
    year: string
    mileage: string
    vin: string | null

    body_type: string
    transmission: string
    engine: string
    fuel_type: ListingFuelType
    color: string

    condition: ListingCondition
    condition_description: string | null
    trim_level: string | null

    purchase_price: number
    additional_expenses: number
    sale_price: number
    discount_amount: number | null

    date_added: string
    deadline_date: string | null
    date_sold: string | null

    status: ListingStatus
    service_note: string | null
    service_start_date: string | null
    service_expected_end_date: string | null
    created_at: string

    total_cost: number
    final_price: number
    net_profit: number
    days_on_lot: number
}

export interface ListingFormInput {
    brand: string
    model: string
    year: string
    mileage: string
    vin?: string

    body_type: string
    transmission: string
    engine: string
    fuel_type: ListingFuelType
    color: string

    condition: ListingCondition
    condition_description?: string
    trim_level?: string

    purchase_price: number
    additional_expenses?: number
    sale_price: number
    discount_amount?: number

    date_added?: string
    deadline_date?: string

    status: ListingStatus

    seller_name?: string
    seller_phone?: string
    seller_email?: string
    seller_social_media?: string
    seller_lead_source?: ClientLeadSource
    employee_id?: number | null
}

export interface MarkListingSoldInput {
    final_sale_price?: number
}

export interface MarkListingOnServiceInput {
    service_note?: string
    service_start_date: string
    service_expected_end_date?: string
}
