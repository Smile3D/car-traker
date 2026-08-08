<script setup lang="ts">
import { ChartPieIcon } from '@heroicons/vue/24/outline'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { Listing, ListingStatus } from '~/types/listings'

ChartJS.register(Title, Tooltip, Legend, ArcElement)

const props = defineProps<{
  listings: Listing[]
  soldCountOverride?: number
  removedCountOverride?: number
}>()

const { t } = useI18n()

const STATUS_ORDER: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed', 'on_service']

// Same override mechanism as ListingStatusCountsGrid (see that component's
// comment for the full rationale) — sold/removed come from the caller's
// DealHistory-sourced counts when provided, since live Listing rows for
// those statuses get deleted by the archive-cleanup job over time.
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

const chartData = computed<ChartData<'doughnut'>>(() => ({
  labels: STATUS_ORDER.map((status) => t(`listingStatus.${status}`)),
  datasets: [
    {
      data: STATUS_ORDER.map((status) => countsByStatus.value[status]),
      backgroundColor: STATUS_ORDER.map((status) => CHART_LISTING_STATUS_COLORS[status]),
      borderWidth: 0,
      hoverOffset: 4,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'doughnut'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { usePointStyle: true, boxWidth: 8 },
    },
    tooltip: {
      callbacks: {
        label: (tooltipItem: TooltipItem<'doughnut'>) => `${tooltipItem.label}: ${tooltipItem.parsed}`,
      },
    },
  },
}))
</script>

<template>
  <div
    v-if="listings.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <ChartPieIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('crm.analytics.noData') }}</p>
  </div>

  <div v-else class="h-80">
    <Doughnut :data="chartData" :options="chartOptions" />
  </div>
</template>
