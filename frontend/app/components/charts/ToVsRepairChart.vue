<script setup lang="ts">
import { ChartPieIcon } from '@heroicons/vue/24/outline'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js'
import type { ChartData, ChartOptions, TooltipItem } from 'chart.js'
import type { ServiceRecord } from '~/types/serviceRecords'

ChartJS.register(Title, Tooltip, Legend, ArcElement)

const props = defineProps<{ serviceRecords: ServiceRecord[] }>()

const { t, n } = useI18n()

const totalsByType = computed<{ maintenance: number, repair: number }>(() => {
  const totals = { maintenance: 0, repair: 0 }

  for (const record of props.serviceRecords) {
    totals[record.record_type] += record.total_cost
  }

  return totals
})

const chartData = computed<ChartData<'doughnut'>>(() => ({
  labels: [t('charts.legend.maintenance'), t('charts.legend.repair')],
  datasets: [
    {
      data: [totalsByType.value.maintenance, totalsByType.value.repair],
      backgroundColor: [CHART_PRIMARY_COLOR, CHART_ACCENT_COLOR],
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
        label: (tooltipItem: TooltipItem<'doughnut'>) => `${tooltipItem.label}: ${n(tooltipItem.parsed, 'currency')}`,
      },
    },
  },
}))
</script>

<template>
  <div
    v-if="serviceRecords.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <ChartPieIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ t('charts.noData') }}</p>
  </div>

  <div v-else class="h-80">
    <Doughnut :data="chartData" :options="chartOptions" />
  </div>
</template>
