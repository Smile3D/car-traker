export type FuelType = 'petrol' | 'diesel' | 'gas' | 'gas_petrol'

export interface Car {
    id: number
    user_id: number
    brand: string
    model: string
    year: string
    mileage: string
    vin: string
    fuel_type: FuelType
    created_at: string
}

export interface CarCreateInput {
    brand: string
    model: string
    year: string
    mileage: string
    vin: string
    fuel_type: FuelType
}
