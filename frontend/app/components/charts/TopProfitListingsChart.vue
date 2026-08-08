<script setup lang="ts">
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { DealHistoryEntry } from '~/types/dealHistory'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ dealHistoryEntries: DealHistoryEntry[] }>()

const { t, n } = useI18n()

// Ranking only ever makes sense across completed sales — a draft/active lot
// has no realized profit yet, so sold-only is correct here even though the
// previous Listing-sourced version didn't filter by status at all.
const topDeals = computed<DealHistoryEntry[]>(() =>
  [...props.dealHistoryEntries]
    .filter((entry) => entry.deal_type === 'sold' && entry.net_profit !== null)
    .sort((a, b) => (b.net_profit ?? 0) - (a.net_profit ?? 0))
    .slice(0, 10)
)

const chartData = computed<ChartData<'bar'>>(() => ({
  labels: topDeals.value.map((entry) => `${entry.brand} ${entry.model}, ${entry.year}`),
  datasets: [
    {
      label: t('crm.analytics.topProfitChart'),
      data: topDeals.value.map((entry) => entry.net_profit ?? 0),
      backgroundColor: CHART_PRIMARY_COLOR,
      borderRadius: 4,
      maxBarThickness: 24,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'bar'>>(() => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (tooltipItem: TooltipItem<'bar'>) => n(tooltipItem.parsed.x ?? 0, 'currency'),
      },
    },
  },
  scales: {
    x: {
      title: { display: true, text: t('crm.analytics.topProfitChart') },
      grid: { color: CHART_GRID_COLOR },
    },
    y: {
      grid: { display: false },
    },
  },
}))
</script>

<template>
  <div
    v-if="topDeals.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <ChartBarIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('crm.analytics.noData') }}</p>
  </div>

  <div v-else class="h-80">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>
