<script setup lang="ts">
import { WrenchScrewdriverIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, d } = useI18n()
const router = useRouter()

const listingStore = useListingStore()

await listingStore.fetchListings()

const onServiceListings = computed<Listing[]>(() =>
  listingStore.listings.filter((listing) => listing.status === 'on_service')
)

const formattedDate = (value: string | null): string => value ? d(new Date(value), 'short') : '—'

function openListingDetails(listing: Listing): void {
  router.push(`/crm/inventory/${listing.id}`)
}

const returnToWorkPendingId = ref<number | null>(null)

function handleReturnToWorkClick(listingId: number): void {
  returnToWorkPendingId.value = listingId
}

async function handleReturnToWorkConfirm(): Promise<void> {
  if (returnToWorkPendingId.value === null) {
    return
  }
  try {
    await listingStore.returnListingToWork(returnToWorkPendingId.value)
  } finally {
    returnToWorkPendingId.value = null
  }
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold text-foreground">{{ t('crm.service.title') }}</h1>

    <!-- ServiceEmptyState -->
    <div
      v-if="onServiceListings.length === 0"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <WrenchScrewdriverIcon class="size-6" />
      </span>
      <div>
        <p class="font-medium text-foreground">{{ t('crm.service.emptyTitle') }}</p>
        <p class="mt-1 text-sm text-muted-foreground">{{ t('crm.service.emptySubtitle') }}</p>
      </div>
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="px-4 py-3 font-medium">{{ t('crm.inventory.columns.car') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.service.columns.startDate') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.service.columns.expectedEndDate') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.service.columns.note') }}</th>
            <th class="px-4 py-3 font-medium" />
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr
            v-for="listing in onServiceListings"
            :key="listing.id"
            class="cursor-pointer transition-colors hover:bg-muted"
            @click="openListingDetails(listing)"
          >
            <td class="px-4 py-3 font-medium text-foreground">
              <div class="flex items-center gap-3">
                <ListingCoverThumbnail :listing-id="listing.id" />
                <span>{{ listing.brand }} {{ listing.model }}, {{ listing.year }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.service_start_date) }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.service_expected_end_date) }}</td>
            <td class="max-w-xs px-4 py-3 text-muted-foreground">
              <span class="line-clamp-2">{{ listing.service_note || '—' }}</span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                type="button"
                class="whitespace-nowrap rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
                @click.stop="handleReturnToWorkClick(listing.id)"
              >
                {{ t('crm.service.returnToWorkButton') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ConfirmDialog
      v-if="returnToWorkPendingId !== null"
      :title="t('crm.service.returnToWorkConfirmTitle')"
      :message="t('crm.service.returnToWorkConfirmMessage')"
      :confirm-label="t('crm.service.returnToWorkButton')"
      @confirm="handleReturnToWorkConfirm"
      @cancel="returnToWorkPendingId = null"
    />
  </div>
</template>
