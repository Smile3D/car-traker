import type { ClientLeadSource } from '~/utils/clientOptions'

export type DealType = 'sold' | 'removed'

// A snapshot at the moment the deal closed — not a live view. Renaming a
// client or an employee later never updates these rows retroactively.
export interface DealHistoryEntry {
    id: number
    listing_id: number | null
    deal_type: DealType

    brand: string
    model: string
    year: string
    vin: string | null

    seller_name: string
    seller_phone: string
    buyer_name: string | null
    buyer_phone: string | null
    seller_lead_source: ClientLeadSource | null
    buyer_lead_source: ClientLeadSource | null

    final_price: number | null
    purchase_price: number | null
    additional_expenses: number | null
    net_profit: number | null

    employee_name: string | null
    employee_id: number | null

    date_closed: string
    date_added: string | null
    days_on_lot: number | null
    created_at: string
}
