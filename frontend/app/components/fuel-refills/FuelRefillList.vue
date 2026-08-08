<script setup lang="ts">
import { PencilSquareIcon, TrashIcon, BeakerIcon } from '@heroicons/vue/24/outline'
import type { FuelType } from '~/types/cars'
import type { FuelRefill } from '~/types/fuelRefills'

const props = defineProps<{
  refills: FuelRefill[]
  carId: number
  fuelType: FuelType
  emptyMessage: string
}>()

const { t, n, d } = useI18n()

const fuelRefillStore = useFuelRefillStore()

const editingFuelRefill = ref<FuelRefill | null>(null)

const unitLabel = computed<string>(() => t(getFuelUnitKey(props.fuelType)))

const formattedCost = (cost: number): string => n(cost, 'currency')
const formattedAmount = (amount: number): string => n(amount, 'decimal')
const formattedMileage = (mileage: number): string => n(mileage, 'decimal')
const formattedDate = (refillDate: string): string => d(new Date(refillDate), 'short')

async function handleDeleteClick(refillId: number): Promise<void> {
  await fuelRefillStore.deleteFuelRefill(props.carId, refillId)
}
</script>

<template>
  <!-- FuelRefillEmptyState -->
  <div
    v-if="refills.length === 0"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
  >
    <BeakerIcon class="size-8 text-muted-foreground" />
    <p class="text-sm text-muted-foreground">{{ emptyMessage }}</p>
  </div>

  <!-- FuelRefillItems -->
  <ul v-else class="space-y-2">
    <!-- FuelRefillItem -->
    <li
      v-for="fuelRefill in refills"
      :key="fuelRefill.id"
      class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-surface p-4"
    >
      <div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-foreground">{{ formattedDate(fuelRefill.refill_date) }}</span>
          <span v-if="fuelRefill.station_name" class="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-foreground">{{ fuelRefill.station_name }}</span>
        </div>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ formattedAmount(fuelRefill.fuel_amount) }} {{ unitLabel }}
          <template v-if="fuelRefill.mileage !== null">
            · {{ formattedMileage(fuelRefill.mileage) }} {{ t('common.units.km') }}
          </template>
        </p>
      </div>

      <div class="flex items-center gap-3">
        <span class="text-sm font-semibold tabular-nums text-foreground">{{ formattedCost(fuelRefill.cost) }}</span>

        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs font-medium text-foreground hover:bg-muted"
          @click="editingFuelRefill = fuelRefill"
        >
          <PencilSquareIcon class="size-3.5" />
          {{ t('common.buttons.edit') }}
        </button>
        <button
          type="button"
          class="flex items-center gap-1 rounded-md border border-destructive/30 px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10"
          @click="handleDeleteClick(fuelRefill.id)"
        >
          <TrashIcon class="size-3.5" />
          {{ t('common.buttons.delete') }}
        </button>
      </div>
    </li>
  </ul>

  <EditFuelRefillModal
    v-if="editingFuelRefill"
    :car-id="carId"
    :fuel-type="fuelType"
    :fuel-refill="editingFuelRefill"
    @close="editingFuelRefill = null"
  />
</template>
