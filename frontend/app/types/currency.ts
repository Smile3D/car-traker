export type RateSource = 'auto' | 'manual'

export interface CurrencyRate {
  auto_rate: number | null
  auto_rate_updated_at: string | null
  manual_rate: number | null
  active_source: RateSource
  active_rate: number | null
}

export interface CurrencySettingsUpdateInput {
  rate_source: RateSource
  manual_rate?: number
}
