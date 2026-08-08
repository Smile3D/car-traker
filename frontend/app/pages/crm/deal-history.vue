<script setup lang="ts">
import { ClipboardDocumentListIcon, MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import type { DealHistoryEntry, DealType } from '~/types/dealHistory'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, n, d } = useI18n()

const dealHistoryStore = useDealHistoryStore()
const route = useRoute()

await dealHistoryStore.fetchDealHistory()

// The backend itself scopes the response to just this employee's deals —
// this is only the UI hint that explains why the list looks narrower than
// the whole company's, same approach as the personal-scope Analytics page.
const { isEmployee } = useUserRole()

const dealTypeOptions: DealType[] = ['sold', 'removed']

const searchQuery = ref('')
const selectedType = ref<DealType | ''>(
  dealTypeOptions.includes(route.query.type as DealType) ? (route.query.type as DealType) : ''
)
const dateFrom = ref('')
const dateTo = ref('')

const typeTabs = computed(() => [
  { value: '' as const, label: t('crm.dealHistory.tabs.all') },
  { value: 'sold' as const, label: t('listingStatus.sold') },
  { value: 'removed' as const, label: t('listingStatus.removed') },
])

const filteredEntries = computed<DealHistoryEntry[]>(() => {
  let result = dealHistoryStore.entries

  if (selectedType.value) {
    result = result.filter((entry) => entry.deal_type === selectedType.value)
  }

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    result = result.filter((entry) =>
      entry.seller_name.toLowerCase().includes(query) || (entry.buyer_name?.toLowerCase().includes(query) ?? false)
    )
  }

  if (dateFrom.value) {
    result = result.filter((entry) => entry.date_closed >= dateFrom.value)
  }
  if (dateTo.value) {
    result = result.filter((entry) => entry.date_closed <= dateTo.value)
  }

  return result
})

const formattedDate = (value: string): string => d(new Date(value), 'short')
const formattedPrice = (value: number): string => n(value, 'currency')
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.dealHistory.title') }}</h1>
      <p v-if="isEmployee" class="mt-1 text-sm text-muted-foreground">{{ t('crm.dealHistory.personalScopeSubtitle') }}</p>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <div class="relative flex-1 sm:max-w-xs">
        <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('crm.dealHistory.searchPlaceholder')"
          class="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <div class="inline-flex gap-1 rounded-md bg-muted p-1">
        <button
          v-for="tab in typeTabs"
          :key="tab.value"
          type="button"
          class="whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="selectedType === tab.value ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
          @click="selectedType = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="flex items-center gap-1.5 text-sm text-muted-foreground">
        <label for="deal-history-date-from">{{ t('crm.dealHistory.dateFromLabel') }}</label>
        <input
          id="deal-history-date-from"
          v-model="dateFrom"
          type="date"
          class="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <label for="deal-history-date-to">{{ t('crm.dealHistory.dateToLabel') }}</label>
        <input
          id="deal-history-date-to"
          v-model="dateTo"
          type="date"
          class="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>
    </div>

    <!-- EmptyState -->
    <div
      v-if="dealHistoryStore.entries.length === 0"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <ClipboardDocumentListIcon class="size-6" />
      </span>
      <p class="text-sm text-muted-foreground">{{ t('crm.dealHistory.emptyState') }}</p>
    </div>

    <!-- FilteredEmptyState -->
    <div
      v-else-if="filteredEntries.length === 0"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <ClipboardDocumentListIcon class="size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ t('crm.dealHistory.emptyFilteredState') }}</p>
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.closedDate') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.type') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.car') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.seller') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.buyer') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.manager') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.dealHistory.columns.finalPrice') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="entry in filteredEntries" :key="entry.id">
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(entry.date_closed) }}</td>
            <td class="px-4 py-3">
              <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="getListingStatusBadgeClasses(entry.deal_type)">
                {{ t(`listingStatus.${entry.deal_type}`) }}
              </span>
            </td>
            <td class="px-4 py-3 font-medium text-foreground">{{ entry.brand }} {{ entry.model }}, {{ entry.year }}</td>
            <td class="px-4 py-3 text-foreground">{{ entry.seller_name }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ entry.buyer_name || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ entry.employee_name || '—' }}</td>
            <td class="px-4 py-3 tabular-nums text-foreground">
              {{ entry.final_price != null ? formattedPrice(entry.final_price) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
