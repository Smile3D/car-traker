export interface FuelRefill {
    id: number
    car_id: number
    refill_date: string
    fuel_amount: number
    cost: number
    mileage: number | null
    station_name: string | null
    created_at: string
}

export interface FuelRefillCreateInput {
    refill_date: string
    fuel_amount: number
    cost: number
    mileage?: number
    station_name?: string
}

export interface FuelRefillUpdateInput {
    refill_date?: string
    fuel_amount?: number
    cost?: number
    mileage?: number
    station_name?: string
}
