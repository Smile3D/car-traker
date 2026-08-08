<script setup lang="ts">
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { ServiceRecord } from '~/types/serviceRecords'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale)

const props = defineProps<{ serviceRecords: ServiceRecord[] }>()

const { t, n } = useI18n()

const totalsByMileage = computed<Map<number, number>>(() => {
  const totals = new Map<number, number>()

  for (const record of props.serviceRecords) {
    totals.set(record.mileage, (totals.get(record.mileage) ?? 0) + record.total_cost)
  }

  return new Map([...totals.entries()].sort(([mileageA], [mileageB]) => mileageA - mileageB))
})

const chartData = computed<ChartData<'line'>>(() => ({
  labels: [...totalsByMileage.value.keys()].map((mileage) => `${n(mileage, 'decimal')} ${t('common.units.km')}`),
  datasets: [
    {
      label: t('charts.datasetLabels.expenses'),
      data: [...totalsByMileage.value.values()],
      borderColor: CHART_PRIMARY_COLOR,
      backgroundColor: CHART_PRIMARY_COLOR,
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
        label: (tooltipItem: TooltipItem<'line'>) => n(tooltipItem.parsed.y ?? 0, 'currency'),
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
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
