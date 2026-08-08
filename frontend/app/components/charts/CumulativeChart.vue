<script setup lang="ts">
import { PresentationChartLineIcon } from '@heroicons/vue/24/outline'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { ServiceRecord } from '~/types/serviceRecords'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale, Filler)

const props = defineProps<{ serviceRecords: ServiceRecord[] }>()

const { t, n, d } = useI18n()

const cumulativePoints = computed<{ date: string, total: number }[]>(() => {
  const sortedRecords = [...props.serviceRecords].sort((a, b) => a.service_date.localeCompare(b.service_date))

  let runningTotal = 0
  return sortedRecords.map((record) => {
    runningTotal += record.total_cost
    return { date: record.service_date, total: runningTotal }
  })
})

const chartData = computed<ChartData<'line'>>(() => ({
  labels: cumulativePoints.value.map((point) => d(new Date(point.date), 'short')),
  datasets: [
    {
      label: t('charts.datasetLabels.cumulative'),
      data: cumulativePoints.value.map((point) => point.total),
      borderColor: CHART_PRIMARY_COLOR,
      backgroundColor: CHART_PRIMARY_FILL,
      pointRadius: 3,
      pointHoverRadius: 5,
      fill: true,
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
        label: (tooltipItem: TooltipItem<'line'>) => n(tooltipItem.parsed.y ?? 0, 'currency'),
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
    },
    y: {
      title: { display: true, text: t('charts.datasetLabels.cumulative') },
      grid: { color: CHART_GRID_COLOR },
    },
  },
}))
</script>

<template>
  <div
    v-if="serviceRecords.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <PresentationChartLineIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('charts.noData') }}</p>
  </div>

  <div v-else class="h-80">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
