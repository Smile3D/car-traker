import type { Receipt } from '~/types/receipts'

type Translate = (key: string, params?: Record<string, unknown>) => string
type FormatDate = (value: Date, key?: string) => string

export function getReceiptLinkLabel(receipt: Receipt, t: Translate, d: FormatDate): string | null {
    if (receipt.service_record) {
        const dateLabel = d(new Date(receipt.service_record.service_date), 'short')
        return receipt.service_record.record_type === 'repair'
            ? t('receipts.linkedToRepair', { date: dateLabel })
            : t('receipts.linkedToMaintenance', { date: dateLabel })
    }

    if (receipt.fuel_refill) {
        return t('receipts.linkedToFuelRefill', { date: d(new Date(receipt.fuel_refill.refill_date), 'short') })
    }

    return null
}
