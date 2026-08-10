<script setup lang="ts">
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  WrenchScrewdriverIcon,
  PencilSquareIcon,
  TrashIcon,
  DocumentTextIcon,
  PlusIcon,
  BeakerIcon,
  PhotoIcon,
} from '@heroicons/vue/24/outline'
import type { RecordType } from '~/types/serviceRecords'

type MainTab = RecordType | 'charts' | 'fuel' | 'receipts'
type ChartType = 'monthly-expenses' | 'to-vs-repair' | 'by-mileage' | 'cumulative'

definePageMeta({ middleware: 'garage-disabled' })

const { t, n, d } = useI18n()

const mainTabs: { type: MainTab, labelKey: string, icon: typeof WrenchScrewdriverIcon }[] = [
  { type: 'maintenance', labelKey: 'serviceRecord.tabs.maintenance', icon: WrenchScrewdriverIcon },
  { type: 'repair', labelKey: 'serviceRecord.tabs.repair', icon: ExclamationTriangleIcon },
  { type: 'fuel', labelKey: 'fuelRefill.tabLabel', icon: BeakerIcon },
  { type: 'receipts', labelKey: 'receipts.tabLabel', icon: PhotoIcon },
  { type: 'charts', labelKey: 'charts.tabLabel', icon: ChartBarIcon },
]

const chartTabs: { type: ChartType, labelKey: string }[] = [
  { type: 'monthly-expenses', labelKey: 'charts.tabs.monthlyExpenses' },
  { type: 'to-vs-repair', labelKey: 'charts.tabs.toVsRepair' },
  { type: 'by-mileage', labelKey: 'charts.tabs.byMileage' },
  { type: 'cumulative', labelKey: 'charts.tabs.cumulative' },
]

const route = useRoute()
const router = useRouter()
const carsStore = useCarStore()
const serviceRecordStore = useServiceRecordStore()
const fuelRefillStore = useFuelRefillStore()

const carId = Number(route.params.id)

const isEditModalOpen = ref(false)
const isReportModalOpen = ref(false)
const isAddFuelRefillModalOpen = ref(false)
const isUploadReceiptModalOpen = ref(false)
const addServiceRecordType = ref<RecordType | null>(null)
const notFound = ref(false)
const activeTab = ref<MainTab>('maintenance')
const activeChart = ref<ChartType>('monthly-expenses')

const car = computed(() => carsStore.cars.find((existingCar) => existingCar.id === carId))

if (Number.isNaN(carId)) {
  notFound.value = true
} else if (!car.value) {
  try {
    await carsStore.fetchCarById(carId)
  } catch {
    notFound.value = true
  }
}

if (!notFound.value) {
  await serviceRecordStore.fetchServiceRecords(carId)
  await fuelRefillStore.fetchFuelRefills(carId)
}

const maintenanceRecords = computed(() =>
  serviceRecordStore.serviceRecords.filter((record) => record.record_type === 'maintenance')
)
const repairRecords = computed(() =>
  serviceRecordStore.serviceRecords.filter((record) => record.record_type === 'repair')
)

const formattedMileage = computed<string>(() => car.value ? n(Number(car.value.mileage), 'decimal') : '')
const formattedCreatedAt = computed<string>(() => car.value ? d(new Date(car.value.created_at), 'short') : '')

const reportText = computed<string>(() => {
  if (!car.value) {
    return ''
  }

  const lines: string[] = []

  lines.push(`🚗 ${car.value.brand} ${car.value.model}, ${car.value.year}`)
  lines.push(`VIN: ${car.value.vin}`)
  lines.push(`${t('report.currentMileage')}: ${n(Number(car.value.mileage), 'decimal')} ${t('common.units.km')}`)
  lines.push('')

  const records = serviceRecordStore.serviceRecords

  if (records.length === 0) {
    lines.push(`📋 ${t('report.noHistory')}`)
  } else {
    lines.push(`📋 ${t('report.historyTitle')} (${t('report.recordsCount', { count: records.length })}):`)
    lines.push('')

    for (const record of records) {
      const typeLabel = record.record_type === 'repair' ? t('charts.legend.repair') : t('charts.legend.maintenance')
      lines.push(`${d(new Date(record.service_date), 'short')} · ${n(record.mileage, 'decimal')} ${t('common.units.km')} · ${typeLabel}`)
      lines.push(record.items.map((item) => item.name).join(', '))
      lines.push('')
    }

    const lastRecord = records[records.length - 1]
    if (lastRecord) {
      lines.push(`${t('report.lastService')}: ${d(new Date(lastRecord.service_date), 'short')} (${n(lastRecord.mileage, 'decimal')} ${t('common.units.km')})`)
    }
  }

  return lines.join('\n')
})

async function handleDeleteClick(): Promise<void> {
  if (!car.value) {
    return
  }

  await carsStore.deleteCar(car.value.id)
  router.push('/garage')
}
</script>

<template>
  <div class="space-y-6">
    <NuxtLink to="/garage" class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeftIcon class="size-4" />
      {{ t('carDetails.backToGarage') }}
    </NuxtLink>

    <!-- ===== CarNotFound ===== -->
    <div
      v-if="notFound"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <ExclamationTriangleIcon class="size-8 text-muted-foreground" />
      <p class="font-medium text-foreground">{{ t('carDetails.notFound') }}</p>
    </div>

    <template v-else-if="car">
      <!-- ===== CarDetailsHeader ===== -->
      <div class="rounded-lg border border-border bg-surface p-5 shadow-card">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold text-foreground">{{ car.brand }} {{ car.model }}</h1>
            <span class="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">{{ car.year }}</span>
          </div>

          <!-- CarDetailsActions -->
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              @click="isEditModalOpen = true"
            >
              <PencilSquareIcon class="size-4" />
              {{ t('common.buttons.edit') }}
            </button>
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              @click="isReportModalOpen = true"
            >
              <DocumentTextIcon class="size-4" />
              {{ t('report.button') }}
            </button>
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
              @click="handleDeleteClick"
            >
              <TrashIcon class="size-4" />
              {{ t('common.buttons.delete') }}
            </button>
          </div>
        </div>

        <!-- CarDetailsStats -->
        <dl class="mt-5 grid grid-cols-1 gap-3 border-t border-border pt-4 sm:grid-cols-3">
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('common.mileage') }}</dt>
            <dd class="mt-0.5 text-base font-semibold tabular-nums text-foreground">{{ formattedMileage }} {{ t('common.units.km') }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('common.vin') }}</dt>
            <dd class="mt-0.5 text-base font-semibold text-foreground">{{ car.vin }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('common.addedAt') }}</dt>
            <dd class="mt-0.5 text-base font-semibold text-foreground">{{ formattedCreatedAt }}</dd>
          </div>
        </dl>
      </div>

      <!-- ===== CarServiceHistorySection ===== -->
      <section class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card">
        <!-- MainTabs -->
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-0">
          <div class="-mb-px flex gap-1 overflow-x-auto">
            <button
              v-for="mainTab in mainTabs"
              :key="mainTab.type"
              type="button"
              class="flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors"
              :class="activeTab === mainTab.type
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'"
              @click="activeTab = mainTab.type"
            >
              <component :is="mainTab.icon" class="size-4" />
              {{ t(mainTab.labelKey) }}
            </button>
          </div>

          <button
            v-if="activeTab === 'maintenance' || activeTab === 'repair'"
            type="button"
            class="mb-2 flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
            @click="addServiceRecordType = activeTab"
          >
            <PlusIcon class="size-4" />
            {{ t('serviceRecord.addRecord') }}
          </button>

          <button
            v-else-if="activeTab === 'fuel'"
            type="button"
            class="mb-2 flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
            @click="isAddFuelRefillModalOpen = true"
          >
            <PlusIcon class="size-4" />
            {{ t('fuelRefill.addRefill') }}
          </button>

          <button
            v-else-if="activeTab === 'receipts'"
            type="button"
            class="mb-2 flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
            @click="isUploadReceiptModalOpen = true"
          >
            <PlusIcon class="size-4" />
            {{ t('receipts.upload') }}
          </button>
        </div>

        <!-- MainTabPanel: ТО -->
        <ServiceRecordList
          v-if="activeTab === 'maintenance'"
          :records="maintenanceRecords"
          :car-id="car.id"
          :empty-message="t('serviceRecord.emptyMaintenance')"
        />

        <!-- MainTabPanel: ремонт -->
        <ServiceRecordList
          v-else-if="activeTab === 'repair'"
          :records="repairRecords"
          :car-id="car.id"
          :empty-message="t('serviceRecord.emptyRepair')"
        />

        <!-- MainTabPanel: заправки -->
        <div v-else-if="activeTab === 'fuel'" class="space-y-4">
          <FuelExpensesChart :fuel-refills="fuelRefillStore.fuelRefills" />

          <FuelRefillList
            :refills="fuelRefillStore.fuelRefills"
            :car-id="car.id"
            :fuel-type="car.fuel_type"
            :empty-message="t('fuelRefill.emptyState')"
          />
        </div>

        <!-- MainTabPanel: чеки -->
        <ReceiptsGallery
          v-else-if="activeTab === 'receipts'"
          :car-id="car.id"
        />

        <!-- MainTabPanel: графики -->
        <div v-else class="space-y-4">
          <!-- ChartTabs -->
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

          <!-- ChartPanel -->
          <MonthlyExpensesChart
            v-if="activeChart === 'monthly-expenses'"
            :service-records="serviceRecordStore.serviceRecords"
          />
          <ToVsRepairChart
            v-else-if="activeChart === 'to-vs-repair'"
            :service-records="serviceRecordStore.serviceRecords"
          />
          <ByMileageChart
            v-else-if="activeChart === 'by-mileage'"
            :service-records="serviceRecordStore.serviceRecords"
          />
          <CumulativeChart
            v-else-if="activeChart === 'cumulative'"
            :service-records="serviceRecordStore.serviceRecords"
          />
        </div>
      </section>

      <EditCarModal
        v-if="isEditModalOpen"
        :car-id="car.id"
        :initial-car="{ brand: car.brand, model: car.model, year: car.year, mileage: car.mileage, vin: car.vin, fuel_type: car.fuel_type }"
        @close="isEditModalOpen = false"
      />

      <AddServiceRecordModal
        v-if="addServiceRecordType"
        :car-id="car.id"
        :record-type="addServiceRecordType"
        @close="addServiceRecordType = null"
      />

      <ReportModal
        v-if="isReportModalOpen"
        :initial-text="reportText"
        @close="isReportModalOpen = false"
      />

      <AddFuelRefillModal
        v-if="isAddFuelRefillModalOpen"
        :car-id="car.id"
        :fuel-type="car.fuel_type"
        @close="isAddFuelRefillModalOpen = false"
      />

      <UploadReceiptModal
        v-if="isUploadReceiptModalOpen"
        :car-id="car.id"
        @close="isUploadReceiptModalOpen = false"
      />
    </template>
  </div>
</template>
