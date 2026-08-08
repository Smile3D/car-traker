<script setup lang="ts">
import { ArrowRightIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, n, d } = useI18n()

const authStore = useAuthStore()
const listingStore = useListingStore()
const dealHistoryStore = useDealHistoryStore()

await Promise.all([listingStore.fetchListings(), dealHistoryStore.fetchDealHistory()])

const { isEmployee } = useUserRole()

// Scope everything below to "my own listings" for an employee — every
// Listing-sourced KPI/chart (current inventory state: active count, overdue
// deadlines, draft/active/reserved counts) derives from this one filtered
// set. Anything DealHistory-sourced (sold/removed counts, profit, margin,
// the profit/days-on-lot charts) does NOT need this filter — the backend
// already scopes GET /deal-history to the employee's own deals, exactly
// like the Deal History page and the Dashboard.
const scopedListings = computed<Listing[]>(() => {
  if (!isEmployee.value) {
    return listingStore.listings
  }
  const currentUserId = authStore.user?.id
  return listingStore.listings.filter((listing) => listing.seller?.employee_id === currentUserId)
})

const soldDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'sold'))
const removedDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'removed'))

type ChartType = 'monthly-profit' | 'status' | 'avg-days' | 'top-profit'

const chartTabs: { type: ChartType, labelKey: string }[] = [
  { type: 'monthly-profit', labelKey: 'crm.analytics.monthlyProfitChart' },
  { type: 'status', labelKey: 'crm.analytics.statusChart' },
  { type: 'avg-days', labelKey: 'crm.analytics.averageDaysToSellChart' },
  { type: 'top-profit', labelKey: 'crm.analytics.topProfitChart' },
]

const activeChart = ref<ChartType>('monthly-profit')

const todayIso = new Date().toISOString().slice(0, 10)

const averageMarginPercent = computed<number | null>(() => {
  const dealsWithCost = soldDeals.value.filter((entry) => {
    const totalCost = (entry.purchase_price ?? 0) + (entry.additional_expenses ?? 0)
    return entry.net_profit !== null && totalCost > 0
  })
  if (dealsWithCost.length === 0) {
    return null
  }

  const totalMargin = dealsWithCost.reduce((sum, entry) => {
    const totalCost = (entry.purchase_price ?? 0) + (entry.additional_expenses ?? 0)
    return sum + ((entry.net_profit ?? 0) / totalCost) * 100
  }, 0)
  return totalMargin / dealsWithCost.length
})

const totalNetProfit = computed<number>(() => soldDeals.value.reduce((sum, entry) => sum + (entry.net_profit ?? 0), 0))

const activeCount = computed<number>(() => scopedListings.value.filter((listing) => listing.status === 'active').length)

const overdueListings = computed<Listing[]>(() =>
  scopedListings.value
    .filter((listing) => listing.status !== 'sold' && listing.deadline_date !== null && listing.deadline_date < todayIso)
    .sort((a, b) => a.deadline_date!.localeCompare(b.deadline_date!))
)

function daysOverdue(deadlineDate: string): number {
  const millisecondsPerDay = 1000 * 60 * 60 * 24
  return Math.round((new Date(todayIso).getTime() - new Date(deadlineDate).getTime()) / millisecondsPerDay)
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.sidebar.analytics') }}</h1>
      <p v-if="isEmployee" class="mt-1 text-sm text-muted-foreground">{{ t('crm.analytics.personalScopeSubtitle') }}</p>
    </div>

    <!-- KpiGrid: owner keeps the compact "active lots" count (the dashboard
         already has the full status breakdown); employee gets the full
         per-status breakdown here instead, since their dashboard view is
         company-wide and doesn't tell them which of THEIR OWN lots are in
         which status. -->
    <div v-if="!isEmployee" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.averageMargin') }}</p>
        <p class="mt-1 text-xl font-semibold tabular-nums text-foreground">
          {{ averageMarginPercent === null ? '—' : `${n(averageMarginPercent, 'decimal')}%` }}
        </p>
      </div>

      <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.totalProfit') }}</p>
        <p
          class="mt-1 text-xl font-semibold tabular-nums"
          :class="totalNetProfit >= 0 ? 'text-success' : 'text-destructive'"
        >
          {{ n(totalNetProfit, 'currency') }}
        </p>
      </div>

      <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.activeCount') }}</p>
        <p class="mt-1 text-xl font-semibold tabular-nums text-foreground">{{ activeCount }}</p>
      </div>

      <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.overdueCount') }}</p>
        <p class="mt-1 text-xl font-semibold tabular-nums" :class="overdueListings.length > 0 ? 'text-destructive' : 'text-foreground'">
          {{ overdueListings.length }}
        </p>
      </div>
    </div>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.averageMargin') }}</p>
          <p class="mt-1 text-xl font-semibold tabular-nums text-foreground">
            {{ averageMarginPercent === null ? '—' : `${n(averageMarginPercent, 'decimal')}%` }}
          </p>
        </div>

        <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.totalProfit') }}</p>
          <p
            class="mt-1 text-xl font-semibold tabular-nums"
            :class="totalNetProfit >= 0 ? 'text-success' : 'text-destructive'"
          >
            {{ n(totalNetProfit, 'currency') }}
          </p>
        </div>

        <div class="rounded-lg border border-border bg-surface p-4 shadow-card">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.overdueCount') }}</p>
          <p class="mt-1 text-xl font-semibold tabular-nums" :class="overdueListings.length > 0 ? 'text-destructive' : 'text-foreground'">
            {{ overdueListings.length }}
          </p>
        </div>
      </div>

      <ListingStatusCountsGrid
        :listings="scopedListings"
        :sold-count-override="soldDeals.length"
        :removed-count-override="removedDeals.length"
      />
    </template>

    <!-- OverdueDeadlinesSection -->
    <section class="space-y-3 rounded-lg border border-border bg-surface p-5 shadow-card">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('crm.analytics.overdueSectionTitle') }}</h2>

      <div
        v-if="overdueListings.length === 0"
        class="flex items-center gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success"
      >
        <CheckCircleIcon class="size-4 shrink-0" />
        <span>{{ t('crm.analytics.noOverdue') }}</span>
      </div>

      <ul v-else class="divide-y divide-border">
        <li
          v-for="listing in overdueListings"
          :key="listing.id"
          class="flex flex-wrap items-center justify-between gap-3 py-3"
        >
          <div class="flex items-center gap-2">
            <ExclamationTriangleIcon class="size-4 shrink-0 text-destructive" />
            <div>
              <p class="text-sm font-medium text-foreground">{{ listing.brand }} {{ listing.model }}, {{ listing.year }}</p>
              <p class="text-xs text-muted-foreground">
                {{ t('crm.analytics.deadlineWas') }}: {{ d(new Date(listing.deadline_date!), 'short') }} ·
                {{ t('crm.analytics.overdueByDays', { count: daysOverdue(listing.deadline_date!) }) }}
              </p>
            </div>
          </div>

          <NuxtLink
            :to="`/crm/inventory/${listing.id}`"
            class="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
          >
            {{ t('crm.analytics.goToListing') }}
            <ArrowRightIcon class="size-3.5" />
          </NuxtLink>
        </li>
      </ul>
    </section>

    <!-- ChartsSection -->
    <section class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card">
      <div class="inline-flex flex-wrap gap-1 rounded-md bg-muted p-1">
        <button
          v-for="chartTab in chartTabs"
          :key="chartTab.type"
          type="button"
          class="whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="activeChart === chartTab.type
            ? 'bg-surface text-foreground shadow-card'
            : 'text-muted-foreground hover:text-foreground'"
          @click="activeChart = chartTab.type"
        >
          {{ t(chartTab.labelKey) }}
        </button>
      </div>

      <MonthlyProfitChart v-if="activeChart === 'monthly-profit'" :deal-history-entries="soldDeals" />
      <ListingStatusChart
        v-else-if="activeChart === 'status'"
        :listings="scopedListings"
        :sold-count-override="soldDeals.length"
        :removed-count-override="removedDeals.length"
      />
      <AverageDaysToSellChart v-else-if="activeChart === 'avg-days'" :deal-history-entries="soldDeals" />
      <TopProfitListingsChart v-else-if="activeChart === 'top-profit'" :deal-history-entries="soldDeals" />
    </section>
  </div>
</template>
