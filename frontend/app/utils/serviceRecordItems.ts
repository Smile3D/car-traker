import type { ServiceRecordItemInput } from '~/types/serviceRecords'

export function areServiceRecordItemsValid(items: ServiceRecordItemInput[]): boolean {
    return items.length > 0 && items.every((item) => item.name.trim() !== '' && item.price >= 0)
}
