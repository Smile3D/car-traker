<script setup lang="ts">
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { ServiceRecord } from '~/types/serviceRecords'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ serviceRecords: ServiceRecord[] }>()

const { t, n } = useI18n()

const monthlyTotals = computed<Map<string, number>>(() => {
  const totals = new Map<string, number>()

  for (const record of props.serviceRecords) {
    const month = record.service_date.slice(0, 7)
    totals.set(month, (totals.get(month) ?? 0) + record.total_cost)
  }

  return new Map([...totals.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})

const chartData = computed<ChartData<'bar'>>(() => ({
  labels: [...monthlyTotals.value.keys()],
  datasets: [
    {
      label: t('charts.datasetLabels.expenses'),
      data: [...monthlyTotals.value.values()],
      backgroundColor: CHART_PRIMARY_COLOR,
      borderRadius: 4,
      maxBarThickness: 40,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'bar'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (tooltipItem: TooltipItem<'bar'>) => n(tooltipItem.parsed.y ?? 0, 'currency'),
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
    },
    y: {
      title: { display: true, text: t('charts.datasetLabels.expenses') },
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
    <ChartBarIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('charts.noData') }}</p>
  </div>

  <div v-else class="h-80">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>
