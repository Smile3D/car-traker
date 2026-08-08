<script setup lang="ts">
definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, n } = useI18n()

const listingStore = useListingStore()
const dealHistoryStore = useDealHistoryStore()

const { isCompanyAdmin } = useUserRole()

await Promise.all([listingStore.fetchListings(), dealHistoryStore.fetchDealHistory()])

// Sourced from DealHistory, not Listing — the archive-cleanup job (every 30
// days) deletes every sold/removed Listing row, so counting live Listings
// here would drift toward zero over time. DealHistory is the indestructible
// snapshot log designed to survive exactly that. Reusing the same store the
// Deal History page uses also means it's already scoped identically
// (owner sees the whole company, employee sees only their own deals) —
// these numbers are guaranteed to match that page for the same user.
const soldDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'sold'))
const removedDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'removed'))

const totalNetProfitSold = computed<number>(() =>
  soldDeals.value.reduce((sum, entry) => sum + (entry.net_profit ?? 0), 0)
)
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold text-foreground">{{ t('crm.dashboard.title') }}</h1>

    <ListingStatusCountsGrid
      :listings="listingStore.listings"
      :sold-count-override="soldDeals.length"
      :removed-count-override="removedDeals.length"
      sold-removed-target="deal-history"
    />

    <!-- TotalNetProfitCard -->
    <div v-if="isCompanyAdmin" class="max-w-sm rounded-lg border border-border bg-surface p-5 shadow-card">
      <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.dashboard.totalNetProfit') }}</p>
      <p
        class="mt-1 text-2xl font-semibold tabular-nums"
        :class="totalNetProfitSold >= 0 ? 'text-success' : 'text-destructive'"
      >
        {{ n(totalNetProfitSold, 'currency') }}
      </p>
    </div>
  </div>
</template>
