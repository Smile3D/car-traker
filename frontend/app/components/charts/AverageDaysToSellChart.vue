<script setup lang="ts">
import { PresentationChartLineIcon } from '@heroicons/vue/24/outline'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { DealHistoryEntry } from '~/types/dealHistory'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale)

const props = defineProps<{ dealHistoryEntries: DealHistoryEntry[] }>()

const { t, n } = useI18n()

// days_on_lot is null for any deal recorded before the date_added snapshot
// existed AND whose Listing has since been deleted (unrecoverable) — those
// are excluded here rather than treated as 0, which would silently drag
// the monthly average down.
const soldDealsWithDaysOnLot = computed<DealHistoryEntry[]>(() =>
  props.dealHistoryEntries.filter((entry) => entry.deal_type === 'sold' && entry.date_closed && entry.days_on_lot !== null)
)

const averageDaysByMonth = computed<Map<string, number>>(() => {
  const daysByMonth = new Map<string, number[]>()

  for (const entry of soldDealsWithDaysOnLot.value) {
    const month = entry.date_closed.slice(0, 7)
    const existingDays = daysByMonth.get(month) ?? []
    existingDays.push(entry.days_on_lot!)
    daysByMonth.set(month, existingDays)
  }

  const averages = new Map<string, number>()
  for (const [month, daysList] of daysByMonth) {
    averages.set(month, daysList.reduce((sum, days) => sum + days, 0) / daysList.length)
  }

  return new Map([...averages.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})

const chartData = computed<ChartData<'line'>>(() => ({
  labels: [...averageDaysByMonth.value.keys()],
  datasets: [
    {
      label: t('crm.analytics.averageDaysToSellChart'),
      data: [...averageDaysByMonth.value.values()],
      borderColor: CHART_ACCENT_COLOR,
      backgroundColor: CHART_ACCENT_COLOR,
      pointRadius: 4,
      pointHoverRadius: 6,
      tension: 0.2,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (tooltipItem: TooltipItem<'line'>) => `${n(tooltipItem.parsed.y ?? 0, 'decimal')} ${t('crm.analytics.days')}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
    },
    y: {
      title: { display: true, text: t('crm.analytics.days') },
      grid: { color: CHART_GRID_COLOR },
    },
  },
}))
</script>

<template>
  <div
    v-if="soldDealsWithDaysOnLot.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <PresentationChartLineIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('crm.analytics.noSoldData') }}</p>
  </div>

  <div v-else class="h-80">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
