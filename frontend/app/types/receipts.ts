import type { RecordType } from '~/types/serviceRecords'

export interface LinkedServiceRecord {
    id: number
    record_type: RecordType
    service_date: string
    mileage: number
}

export interface LinkedFuelRefill {
    id: number
    refill_date: string
    fuel_amount: number
    cost: number
}

export interface Receipt {
    id: number
    car_id: number
    description: string | null
    uploaded_at: string
    service_record_id: number | null
    fuel_refill_id: number | null
    service_record: LinkedServiceRecord | null
    fuel_refill: LinkedFuelRefill | null
}
