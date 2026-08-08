<script setup lang="ts">
import { ChevronDownIcon, PencilSquareIcon, TrashIcon, ClipboardDocumentListIcon } from '@heroicons/vue/24/outline'
import type { ServiceRecord } from '~/types/serviceRecords'

const props = defineProps<{
  records: ServiceRecord[]
  carId: number
  emptyMessage: string
}>()

const { t, n, d } = useI18n()

const serviceRecordStore = useServiceRecordStore()

const expandedServiceRecordIds = ref<Set<number>>(new Set())
const editingServiceRecord = ref<ServiceRecord | null>(null)

function toggleServiceRecord(recordId: number): void {
  if (expandedServiceRecordIds.value.has(recordId)) {
    expandedServiceRecordIds.value.delete(recordId)
  } else {
    expandedServiceRecordIds.value.add(recordId)
  }
}

const formattedPrice = (price: number): string => n(price, 'currency')
const formattedMileage = (mileage: number): string => n(mileage, 'decimal')
const formattedServiceDate = (serviceDate: string): string => d(new Date(serviceDate), 'short')

async function handleDeleteClick(recordId: number): Promise<void> {
  await serviceRecordStore.deleteServiceRecord(props.carId, recordId)
}
</script>

<template>
  <!-- ServiceRecordEmptyState -->
  <div
    v-if="records.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <ClipboardDocumentListIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ emptyMessage }}</p>
  </div>

  <!-- ServiceRecordItems -->
  <ul v-else class="space-y-2">
    <!-- ServiceRecordItem -->
    <li
      v-for="serviceRecord in records"
      :key="serviceRecord.id"
      class="rounded-md border border-border bg-surface"
    >
      <!-- ServiceRecordHeader -->
      <button
        type="button"
        class="flex w-full items-center justify-between gap-2 p-4 text-left"
        @click="toggleServiceRecord(serviceRecord.id)"
      >
        <div class="flex items-center gap-2">
          <span class="rounded-md bg-muted px-2 py-0.5 text-xs font-medium tabular-nums text-foreground">{{ formattedMileage(serviceRecord.mileage) }} {{ t('common.units.km') }}</span>
          <span class="text-sm text-muted-foreground">{{ formattedServiceDate(serviceRecord.service_date) }}</span>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold tabular-nums text-foreground">{{ formattedPrice(serviceRecord.total_cost) }}</span>
          <ChevronDownIcon
            class="size-4 text-muted-foreground transition-transform"
            :class="{ 'rotate-180': expandedServiceRecordIds.has(serviceRecord.id) }"
          />
        </div>
      </button>

      <!-- ServiceRecordDetails -->
      <div
        v-if="expandedServiceRecordIds.has(serviceRecord.id)"
        class="border-t border-border p-4"
      >
        <!-- ServiceRecordItemsBreakdown -->
        <ul class="space-y-1">
          <li
            v-for="item in serviceRecord.items"
            :key="item.id"
            class="flex justify-between text-sm"
          >
            <span class="text-foreground">{{ item.name }}</span>
            <span class="tabular-nums text-muted-foreground">{{ formattedPrice(item.price) }}</span>
          </li>
        </ul>

        <div class="mt-2 flex justify-between border-t border-border pt-2 text-sm font-semibold text-foreground">
          <span>{{ t('serviceRecord.total') }}</span>
          <span class="tabular-nums">{{ formattedPrice(serviceRecord.total_cost) }}</span>
        </div>

        <div class="mt-3 flex justify-end gap-2">
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs font-medium text-foreground hover:bg-muted"
            @click="editingServiceRecord = serviceRecord"
          >
            <PencilSquareIcon class="size-3.5" />
            {{ t('common.buttons.edit') }}
          </button>
          <button
            type="button"
            class="flex items-center gap-1 rounded-md border border-destructive/30 px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10"
            @click="handleDeleteClick(serviceRecord.id)"
          >
            <TrashIcon class="size-3.5" />
            {{ t('common.buttons.delete') }}
          </button>
        </div>
      </div>
    </li>
  </ul>

  <EditServiceRecordModal
    v-if="editingServiceRecord"
    :car-id="carId"
    :service-record="editingServiceRecord"
    @close="editingServiceRecord = null"
  />
</template>
