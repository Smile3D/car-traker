export type RecordType = 'maintenance' | 'repair'

export interface ServiceRecordItem {
    id: number
    name: string
    price: number
}

export interface ServiceRecordItemInput {
    name: string
    price: number
}

export interface ServiceRecord {
    id: number
    car_id: number
    record_type: RecordType
    service_date: string
    mileage: number
    items: ServiceRecordItem[]
    total_cost: number
    created_at: string
}

export interface ServiceRecordCreateInput {
    record_type: RecordType
    service_date: string
    mileage: number
    items: ServiceRecordItemInput[]
}

export interface ServiceRecordUpdateInput {
    record_type?: RecordType
    service_date?: string
    mileage?: number
    items?: ServiceRecordItemInput[]
}
