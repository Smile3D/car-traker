<script setup lang="ts">
import type { Listing } from '~/types/listings'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

// Two variants share the same shell (thumbnail, status badge, click-to-open
// row) but differ in which columns matter: inventory cares about how long a
// lot has been sitting and its deadline; archive cares about when/how it
// closed, who was involved, and supports bulk selection for delete.
const props = defineProps<{
  listings: Listing[]
  variant: 'inventory' | 'archive'
  sellerNameFor?: (listing: Listing) => string | undefined
  buyerNameFor?: (listing: Listing) => string | undefined
}>()

const emit = defineEmits<{ select: [listing: Listing] }>()

// Only meaningful (and only rendered) for variant="archive" — bulk-select
// state lives in the parent page so it can drive the "N selected" action bar.
const selectedIds = defineModel<number[]>('selectedIds', { default: () => [] })

const { t, n, d } = useI18n()

const formattedPrice = (price: number): string => n(price, 'currency')
const formattedDate = (value: string | null): string => value ? d(new Date(value), 'short') : '—'

const isAllVisibleSelected = computed<boolean>(() =>
  props.listings.length > 0 && props.listings.every((listing) => selectedIds.value.includes(listing.id))
)

function toggleSelectAll(): void {
  if (isAllVisibleSelected.value) {
    const visibleIds = new Set(props.listings.map((listing) => listing.id))
    selectedIds.value = selectedIds.value.filter((id) => !visibleIds.has(id))
  } else {
    const combinedIds = new Set(selectedIds.value)
    for (const listing of props.listings) {
      combinedIds.add(listing.id)
    }
    selectedIds.value = [...combinedIds]
  }
}

function toggleSelect(listingId: number): void {
  selectedIds.value = selectedIds.value.includes(listingId)
    ? selectedIds.value.filter((id) => id !== listingId)
    : [...selectedIds.value, listingId]
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
    <table class="w-full text-left text-sm">
      <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
        <tr>
          <th v-if="variant === 'archive'" class="w-10 px-4 py-3">
            <input
              type="checkbox"
              class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
              :checked="isAllVisibleSelected"
              :aria-label="t('crm.archive.selectAllLabel')"
              @click.stop="toggleSelectAll"
            >
          </th>
          <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.car') }}</th>
          <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.status') }}</th>
          <th v-if="variant === 'archive'" class="px-4 py-3 font-medium">{{ t('crm.archive.columns.closedDate') }}</th>
          <th class="px-4 py-3 font-medium">
            {{ variant === 'archive' ? t('crm.archive.columns.finalPrice') : t('crm.inventory.columns.salePrice') }}
          </th>
          <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.netProfit') }}</th>
          <template v-if="variant === 'inventory'">
            <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.daysOnLot') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.deadline') }}</th>
          </template>
          <template v-else>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.seller') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.buyer') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.manager') }}</th>
          </template>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr
          v-for="listing in listings"
          :key="listing.id"
          class="cursor-pointer transition-colors hover:bg-muted"
          @click="emit('select', listing)"
        >
          <td v-if="variant === 'archive'" class="px-4 py-3">
            <input
              type="checkbox"
              class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
              :checked="selectedIds.includes(listing.id)"
              :aria-label="t('crm.archive.selectRowLabel')"
              @click.stop="toggleSelect(listing.id)"
            >
          </td>
          <td class="px-4 py-3 font-medium text-foreground">
            <div class="flex items-center gap-3">
              <ListingCoverThumbnail :listing-id="listing.id" />
              <span>{{ listing.brand }} {{ listing.model }}, {{ listing.year }}</span>
            </div>
          </td>
          <td class="px-4 py-3">
            <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="getListingStatusBadgeClasses(listing.status)">
              {{ t(`listingStatus.${listing.status}`) }}
            </span>
          </td>
          <td v-if="variant === 'archive'" class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.date_sold) }}</td>
          <td class="px-4 py-3 tabular-nums text-foreground">
            {{ formattedPrice(variant === 'archive' ? listing.final_price : listing.sale_price) }}
          </td>
          <td class="px-4 py-3 tabular-nums" :class="listing.net_profit >= 0 ? 'text-success' : 'text-destructive'">
            {{ formattedPrice(listing.net_profit) }}
          </td>
          <template v-if="variant === 'inventory'">
            <td class="px-4 py-3 tabular-nums text-muted-foreground">{{ listing.days_on_lot }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.deadline_date) }}</td>
          </template>
          <template v-else>
            <td class="px-4 py-3 text-muted-foreground">{{ sellerNameFor?.(listing) || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ buyerNameFor?.(listing) || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">
              {{ getEmployeeDisplayName(listing.seller?.employee, listing.seller?.employee?.email) || '—' }}
            </td>
          </template>
        </tr>
      </tbody>
    </table>
  </div>
</template>
