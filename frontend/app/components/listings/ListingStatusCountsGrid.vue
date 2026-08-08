<script setup lang="ts">
import type { Listing, ListingStatus } from '~/types/listings'

const props = defineProps<{
  listings: Listing[]
  soldCountOverride?: number
  removedCountOverride?: number
  soldRemovedTarget?: 'archive' | 'deal-history'
}>()

const { t } = useI18n()

const statusKeys: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed', 'on_service']

// sold/removed have an override path: the live Listing table gets wiped by
// the archive-cleanup job every 30 days, so a caller with access to the
// indestructible DealHistory log (currently only the Dashboard) passes the
// real historical count in instead of letting it fall back to counting
// (increasingly absent) live Listing rows. draft/active/reserved are never
// touched by that cleanup, so they always come from `listings` — no
// override exists for them because none is needed.
const countsByStatus = computed<Record<ListingStatus, number>>(() => {
  const counts: Record<ListingStatus, number> = { draft: 0, active: 0, reserved: 0, sold: 0, removed: 0, on_service: 0 }
  for (const listing of props.listings) {
    counts[listing.status] += 1
  }
  if (props.soldCountOverride !== undefined) {
    counts.sold = props.soldCountOverride
  }
  if (props.removedCountOverride !== undefined) {
    counts.removed = props.removedCountOverride
  }
  return counts
})

// Sold/removed lots live in the Archive, not Inventory, now — unless the
// caller (currently only the Dashboard) opts into linking straight to the
// Deal History log instead via soldRemovedTarget. on_service lots live on
// their own dedicated СТО page, same idea.
const archiveStatuses: ListingStatus[] = ['sold', 'removed']
function linkFor(statusKey: ListingStatus): string {
  if (archiveStatuses.includes(statusKey)) {
    return props.soldRemovedTarget === 'deal-history'
      ? `/crm/deal-history?type=${statusKey}`
      : `/crm/archive?status=${statusKey}`
  }
  if (statusKey === 'on_service') {
    return '/crm/service'
  }
  return `/crm/inventory?status=${statusKey}`
}
</script>

<template>
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
    <NuxtLink
      v-for="statusKey in statusKeys"
      :key="statusKey"
      :to="linkFor(statusKey)"
      class="rounded-lg border border-border bg-surface p-4 shadow-card transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-elevated"
    >
      <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t(`listingStatus.${statusKey}`) }}</p>
      <p class="mt-1 text-xl font-semibold tabular-nums text-foreground">{{ countsByStatus[statusKey] }}</p>
    </NuxtLink>
  </div>
</template>
