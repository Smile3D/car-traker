<script setup lang="ts">
import { PlusIcon, TruckIcon } from '@heroicons/vue/24/outline'
import type { Listing, ListingStatus } from '~/types/listings'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const listingStore = useListingStore()

// Sold/removed lots live in the Archive, on_service lots live on the СТО
// page now — Inventory is only the "still in play" statuses.
// listingStore.listings stays the single fetched source; this (and the
// status filter below) narrows it locally.
const statusOptions: ListingStatus[] = ['draft', 'active', 'reserved']
const selectedStatus = ref<ListingStatus | ''>(
  statusOptions.includes(route.query.status as ListingStatus) ? (route.query.status as ListingStatus) : ''
)

await listingStore.fetchListings()

const inventoryListings = computed<Listing[]>(() =>
  listingStore.listings.filter((listing) => statusOptions.includes(listing.status))
)

const filteredListings = computed<Listing[]>(() =>
  selectedStatus.value ? inventoryListings.value.filter((listing) => listing.status === selectedStatus.value) : inventoryListings.value
)

async function handleStatusFilterChange(): Promise<void> {
  await router.replace({ query: selectedStatus.value ? { status: selectedStatus.value } : {} })
}

function openListingDetails(listing: Listing): void {
  router.push(`/crm/inventory/${listing.id}`)
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.inventory.title') }}</h1>

      <div class="flex items-center gap-2">
        <select
          v-model="selectedStatus"
          class="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          @change="handleStatusFilterChange"
        >
          <option value="">{{ t('crm.inventory.filterAll') }}</option>
          <option v-for="statusOption in statusOptions" :key="statusOption" :value="statusOption">
            {{ t(`listingStatus.${statusOption}`) }}
          </option>
        </select>

        <NuxtLink
          to="/crm/inventory/new"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
        >
          <PlusIcon class="size-4" />
          {{ t('crm.inventory.addButton') }}
        </NuxtLink>
      </div>
    </div>

    <!-- InventoryEmptyState -->
    <div
      v-if="inventoryListings.length === 0"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <TruckIcon class="size-6" />
      </span>
      <div>
        <p class="font-medium text-foreground">{{ t('crm.inventory.emptyTitle') }}</p>
        <p class="mt-1 text-sm text-muted-foreground">{{ t('crm.inventory.emptySubtitle') }}</p>
      </div>
      <NuxtLink
        to="/crm/inventory/new"
        class="mt-2 flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
      >
        <PlusIcon class="size-4" />
        {{ t('crm.inventory.addButton') }}
      </NuxtLink>
    </div>

    <!-- InventoryFilteredEmptyState -->
    <div
      v-else-if="filteredListings.length === 0"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <TruckIcon class="size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ t('crm.inventory.emptyFilteredState') }}</p>
    </div>

    <ListingsTable v-else variant="inventory" :listings="filteredListings" @select="openListingDetails" />
  </div>
</template>
