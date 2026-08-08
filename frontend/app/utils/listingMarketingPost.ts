import type { Listing } from '~/types/listings'
import { getListingFuelTypeLabelKey, getTransmissionLabelKey } from '~/utils/listingOptions'

type Translate = (key: string) => string
type FormatCurrency = (value: number) => string

// Deliberately excludes purchase_price, additional_expenses, total_cost, and
// net_profit — this text is meant to be posted publicly, so no internal
// cost/profit figures belong in it. Only final_price (what the buyer pays)
// is shown.
export function generateListingMarketingPost(
    listing: Listing,
    businessPhone: string | null | undefined,
    translate: Translate,
    formatCurrency: FormatCurrency
): string {
    const lines: string[] = []

    lines.push(`🚗 ${listing.brand} ${listing.model}, ${listing.year}`)
    lines.push(`💰 ${formatCurrency(listing.final_price)}`)
    lines.push(`🏁 Пробіг: ${listing.mileage} км`)

    const transmissionLabelKey = getTransmissionLabelKey(listing.transmission)
    lines.push(`⚙️ Коробка передач: ${transmissionLabelKey ? translate(transmissionLabelKey) : listing.transmission}`)

    lines.push(`⛽ Паливо: ${translate(getListingFuelTypeLabelKey(listing.fuel_type))}`)
    lines.push(`🎨 Колір: ${listing.color}`)

    if (listing.condition_description) {
        lines.push(`📝 ${listing.condition_description}`)
    }

    if (listing.trim_level) {
        lines.push(`🔧 Комплектація: ${listing.trim_level}`)
    }

    if (businessPhone) {
        lines.push(`📞 ${businessPhone}`)
    }

    return lines.join('\n')
}
