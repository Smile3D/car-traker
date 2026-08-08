<script setup lang="ts">
import { ArchiveBoxIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, d } = useI18n()
const route = useRoute()
const router = useRouter()

const listingStore = useListingStore()
const clientStore = useClientStore()
const archiveCleanupScheduleStore = useArchiveCleanupScheduleStore()

type ArchiveStatus = 'sold' | 'removed'
const archiveStatuses: ArchiveStatus[] = ['sold', 'removed']

const selectedStatus = ref<ArchiveStatus | ''>(
  archiveStatuses.includes(route.query.status as ArchiveStatus) ? (route.query.status as ArchiveStatus) : ''
)

// listingStore.listings/clientStore.clients stay the single fetched source
// (per both stores' own convention) — status/tab filtering and the seller/
// buyer name lookups below all happen locally, never a separate request.
await Promise.all([listingStore.fetchListings(), clientStore.fetchClients(), archiveCleanupScheduleStore.fetchSchedule()])

const nextCleanupDateFormatted = computed<string>(() => {
  const nextCleanupAt = archiveCleanupScheduleStore.schedule?.next_cleanup_at
  return nextCleanupAt ? d(new Date(nextCleanupAt), 'short') : '—'
})

const archivedListings = computed<Listing[]>(() =>
  listingStore.listings.filter((listing) => archiveStatuses.includes(listing.status as ArchiveStatus))
)

const filteredListings = computed<Listing[]>(() =>
  selectedStatus.value
    ? archivedListings.value.filter((listing) => listing.status === selectedStatus.value)
    : archivedListings.value
)

const archiveTabs = computed(() => [
  { value: '' as const, label: t('crm.archive.tabs.all') },
  { value: 'sold' as const, label: t('listingStatus.sold') },
  { value: 'removed' as const, label: t('listingStatus.removed') },
])

async function selectTab(value: ArchiveStatus | ''): Promise<void> {
  selectedStatus.value = value
  // A selected row might not even be in the new filter's view anymore.
  selectedIds.value = []
  await router.replace({ query: value ? { status: value } : {} })
}

function openListingDetails(listing: Listing): void {
  router.push(`/crm/inventory/${listing.id}`)
}

function sellerNameFor(listing: Listing): string | undefined {
  return clientStore.clients.find((client) => client.listing_id === listing.id && client.client_type === 'seller')?.name
}

function buyerNameFor(listing: Listing): string | undefined {
  return clientStore.clients.find((client) => client.listing_id === listing.id && client.client_type === 'buyer')?.name
}

const selectedIds = ref<number[]>([])
const isBulkDeleteConfirmOpen = ref(false)
const isBulkDeleting = ref(false)
const bulkDeleteSkippedMessages = ref<string[]>([])

async function handleBulkDeleteConfirm(): Promise<void> {
  isBulkDeleting.value = true
  try {
    const { skippedMessages } = await listingStore.bulkDeleteListings(selectedIds.value)
    bulkDeleteSkippedMessages.value = skippedMessages
    selectedIds.value = []
  } finally {
    isBulkDeleting.value = false
    isBulkDeleteConfirmOpen.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.archive.title') }}</h1>

      <div class="inline-flex gap-1 rounded-md bg-muted p-1">
        <button
          v-for="tab in archiveTabs"
          :key="tab.value"
          type="button"
          class="whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="selectedStatus === tab.value ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
          @click="selectTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <WarningBanner>{{ t('crm.archive.autoCleanupWarning', { date: nextCleanupDateFormatted }) }}</WarningBanner>

    <!-- ArchiveEmptyState -->
    <div
      v-if="archivedListings.length === 0"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <ArchiveBoxIcon class="size-6" />
      </span>
      <div>
        <p class="font-medium text-foreground">{{ t('crm.archive.emptyTitle') }}</p>
        <p class="mt-1 text-sm text-muted-foreground">{{ t('crm.archive.emptySubtitle') }}</p>
      </div>
    </div>

    <!-- ArchiveFilteredEmptyState -->
    <div
      v-else-if="filteredListings.length === 0"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <ArchiveBoxIcon class="size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ t('crm.archive.emptyFilteredState') }}</p>
    </div>

    <template v-else>
      <!-- BulkDeleteSkippedNotice -->
      <div
        v-if="bulkDeleteSkippedMessages.length > 0"
        class="flex items-start justify-between gap-2 rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
        role="alert"
      >
        <ul class="list-disc space-y-1 pl-4">
          <li v-for="message in bulkDeleteSkippedMessages" :key="message">{{ message }}</li>
        </ul>
        <button type="button" class="shrink-0 font-medium hover:underline" @click="bulkDeleteSkippedMessages = []">
          {{ t('common.buttons.close') }}
        </button>
      </div>

      <!-- BulkActionsBar -->
      <div
        v-if="selectedIds.length > 0"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3"
      >
        <span class="text-sm font-medium text-foreground">{{ t('crm.archive.selectedCount', { count: selectedIds.length }) }}</span>
        <button
          type="button"
          class="rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          @click="isBulkDeleteConfirmOpen = true"
        >
          {{ t('crm.archive.deleteSelectedButton') }}
        </button>
      </div>

      <ListingsTable
        v-model:selected-ids="selectedIds"
        variant="archive"
        :listings="filteredListings"
        :seller-name-for="sellerNameFor"
        :buyer-name-for="buyerNameFor"
        @select="openListingDetails"
      />
    </template>

    <ConfirmDialog
      v-if="isBulkDeleteConfirmOpen"
      :title="t('crm.archive.bulkDeleteConfirmTitle')"
      :message="t('crm.archive.bulkDeleteConfirmMessage', { count: selectedIds.length })"
      :confirm-label="isBulkDeleting ? t('common.buttons.deleting') : t('crm.archive.deleteSelectedButton')"
      @confirm="handleBulkDeleteConfirm"
      @cancel="isBulkDeleteConfirmOpen = false"
    />
  </div>
</template>
