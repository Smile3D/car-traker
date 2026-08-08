export const LISTING_BODY_TYPES = ['sedan', 'hatchback', 'suv', 'universal', 'coupe', 'minivan', 'pickup', 'cabriolet'] as const
export type ListingBodyType = typeof LISTING_BODY_TYPES[number]

export const LISTING_TRANSMISSIONS = ['manual', 'automatic', 'tiptronic', 'robot', 'variator', 'reductor'] as const
export type ListingTransmission = typeof LISTING_TRANSMISSIONS[number]

export const LISTING_FUEL_TYPES = [
  'petrol',
  'diesel',
  'electric',
  'gas',
  'gas_propane_petrol',
  'gas_methane_petrol',
  'hybrid_hev',
  'hybrid_phev',
  'hybrid_mhev',
  'hybrid_reev',
] as const
export type ListingFuelType = typeof LISTING_FUEL_TYPES[number]

export const OTHER_OPTION_VALUE = '__other__'

const BODY_TYPE_LABEL_KEYS: Record<ListingBodyType, string> = {
  sedan: 'listingOptions.bodyType.sedan',
  hatchback: 'listingOptions.bodyType.hatchback',
  suv: 'listingOptions.bodyType.suv',
  universal: 'listingOptions.bodyType.universal',
  coupe: 'listingOptions.bodyType.coupe',
  minivan: 'listingOptions.bodyType.minivan',
  pickup: 'listingOptions.bodyType.pickup',
  cabriolet: 'listingOptions.bodyType.cabriolet',
}

const TRANSMISSION_LABEL_KEYS: Record<ListingTransmission, string> = {
  manual: 'listingOptions.transmission.manual',
  automatic: 'listingOptions.transmission.automatic',
  tiptronic: 'listingOptions.transmission.tiptronic',
  robot: 'listingOptions.transmission.robot',
  variator: 'listingOptions.transmission.variator',
  reductor: 'listingOptions.transmission.reductor',
}

const FUEL_TYPE_LABEL_KEYS: Record<ListingFuelType, string> = {
  petrol: 'listingOptions.fuelType.petrol',
  diesel: 'listingOptions.fuelType.diesel',
  electric: 'listingOptions.fuelType.electric',
  gas: 'listingOptions.fuelType.gas',
  gas_propane_petrol: 'listingOptions.fuelType.gasPropanePetrol',
  gas_methane_petrol: 'listingOptions.fuelType.gasMethanePetrol',
  hybrid_hev: 'listingOptions.fuelType.hybridHev',
  hybrid_phev: 'listingOptions.fuelType.hybridPhev',
  hybrid_mhev: 'listingOptions.fuelType.hybridMhev',
  hybrid_reev: 'listingOptions.fuelType.hybridReev',
}

export function isKnownBodyType(value: string): value is ListingBodyType {
  return (LISTING_BODY_TYPES as readonly string[]).includes(value)
}

export function isKnownTransmission(value: string): value is ListingTransmission {
  return (LISTING_TRANSMISSIONS as readonly string[]).includes(value)
}

export function getBodyTypeLabelKey(value: string): string | undefined {
  return isKnownBodyType(value) ? BODY_TYPE_LABEL_KEYS[value] : undefined
}

export function getTransmissionLabelKey(value: string): string | undefined {
  return isKnownTransmission(value) ? TRANSMISSION_LABEL_KEYS[value] : undefined
}

export function getListingFuelTypeLabelKey(value: ListingFuelType): string {
  return FUEL_TYPE_LABEL_KEYS[value]
}
