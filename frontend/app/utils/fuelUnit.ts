import type { FuelType } from '~/types/cars'

// Все текущие типы топлива измеряются в литрах. Ключ переведён отдельно,
// чтобы при добавлении electric/hybrid было достаточно добавить новую запись (кВт·ч).
const FUEL_UNIT_KEYS: Record<FuelType, string> = {
  petrol: 'common.units.liters',
  diesel: 'common.units.liters',
  gas: 'common.units.liters',
  gas_petrol: 'common.units.liters',
}

export function getFuelUnitKey(fuelType: FuelType): string {
  return FUEL_UNIT_KEYS[fuelType]
}
