import type { ListingCondition } from '~/types/listings'

const CONDITION_LABEL_KEYS: Record<ListingCondition, string> = {
  new: 'listingForm.conditionNew',
  used: 'listingForm.conditionUsed',
}

export function getListingConditionLabelKey(condition: ListingCondition): string {
  return CONDITION_LABEL_KEYS[condition]
}
