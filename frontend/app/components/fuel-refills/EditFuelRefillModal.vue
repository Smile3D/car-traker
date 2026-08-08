<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useForm, useField } from 'vee-validate'
import type { FuelType } from '~/types/cars'
import type { FuelRefill } from '~/types/fuelRefills'

const props = defineProps<{ carId: number, fuelType: FuelType, fuelRefill: FuelRefill }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const validators = createValidators(t)

const fuelRefillStore = useFuelRefillStore()
const carsStore = useCarStore()

const isKnownStation = props.fuelRefill.station_name !== null
  && (FUEL_STATION_BRANDS as readonly string[]).includes(props.fuelRefill.station_name)

const { meta, handleSubmit } = useForm()

const { value: refillDate, errorMessage: refillDateError } = useField<string>('refill_date', validators.required, { initialValue: props.fuelRefill.refill_date })
const { value: fuelAmount, errorMessage: fuelAmountError } = useField<number | ''>('fuel_amount', validators.positiveNumber, { initialValue: props.fuelRefill.fuel_amount })
const { value: cost, errorMessage: costError } = useField<number | ''>('cost', validators.nonNegativeNumber, { initialValue: props.fuelRefill.cost })
const { value: mileage, errorMessage: mileageError } = useField<number | ''>('mileage', validators.optionalNonNegativeNumber, { initialValue: props.fuelRefill.mileage ?? '' })

const selectedStation = ref(
  !props.fuelRefill.station_name
    ? ''
    : isKnownStation
      ? props.fuelRefill.station_name
      : FUEL_STATION_OTHER_VALUE
)
const customStationName = ref(isKnownStation ? '' : (props.fuelRefill.station_name ?? ''))

const unitLabel = computed<string>(() => t(getFuelUnitKey(props.fuelType)))

const stationName = computed<string | undefined>(() => {
  if (selectedStation.value === FUEL_STATION_OTHER_VALUE) {
    return customStationName.value || undefined
  }
  return selectedStation.value || undefined
})

const saveFuelRefill = handleSubmit(async () => {
  try {
    await fuelRefillStore.updateFuelRefill(props.carId, props.fuelRefill.id, {
      refill_date: refillDate.value,
      fuel_amount: Number(fuelAmount.value),
      cost: Number(cost.value),
      mileage: mileage.value === '' ? undefined : Number(mileage.value),
      station_name: stationName.value,
    })
    await carsStore.fetchCarById(props.carId)
    emit('close')
  } catch {
    // ошибка уже сохранена в fuelRefillStore.error и показана в форме
  }
})
</script>

<template>
  <BaseModal :title="t('fuelRefill.editTitle')" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="saveFuelRefill">
      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-refill-date">{{ t('serviceRecordForm.dateLabel') }} <RequiredMark /></label>
        <input
          id="edit-refill-date"
          v-model="refillDate"
          type="date"
          aria-required="true"
          :aria-invalid="!!refillDateError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="refillDateError" class="mt-1 text-xs text-destructive">{{ refillDateError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-fuel-amount">{{ t('fuelRefill.amountLabel') }} ({{ unitLabel }}) <RequiredMark /></label>
        <input
          id="edit-fuel-amount"
          v-model.number="fuelAmount"
          type="number"
          min="0"
          step="0.01"
          aria-required="true"
          :aria-invalid="!!fuelAmountError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="fuelAmountError" class="mt-1 text-xs text-destructive">{{ fuelAmountError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-cost">{{ t('fuelRefill.costLabel') }} <RequiredMark /></label>
        <input
          id="edit-cost"
          v-model.number="cost"
          type="number"
          min="0"
          step="0.01"
          aria-required="true"
          :aria-invalid="!!costError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="costError" class="mt-1 text-xs text-destructive">{{ costError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-mileage">{{ t('fuelRefill.mileageLabel') }}</label>
        <input
          id="edit-mileage"
          v-model.number="mileage"
          type="number"
          min="0"
          step="1"
          :aria-invalid="!!mileageError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="mileageError" class="mt-1 text-xs text-destructive">{{ mileageError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-station">{{ t('fuelRefill.stationLabel') }}</label>
        <select
          id="edit-station"
          v-model="selectedStation"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">—</option>
          <option v-for="brand in FUEL_STATION_BRANDS" :key="brand" :value="brand">{{ brand }}</option>
          <option :value="FUEL_STATION_OTHER_VALUE">{{ t('fuelRefill.stationOther') }}</option>
        </select>

        <input
          v-if="selectedStation === FUEL_STATION_OTHER_VALUE"
          v-model="customStationName"
          type="text"
          :placeholder="t('fuelRefill.stationOtherPlaceholder')"
          class="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <!-- ErrorAlert -->
      <div
        v-if="fuelRefillStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ fuelRefillStore.error }}</span>
      </div>

      <div class="flex gap-2 border-t border-border pt-4">
        <button
          type="button"
          class="flex-1 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
          @click="emit('close')"
        >
          {{ t('common.buttons.cancel') }}
        </button>
        <button
          type="submit"
          :disabled="fuelRefillStore.isLoading || !meta.valid"
          class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ fuelRefillStore.isLoading ? t('common.buttons.saving') : t('common.buttons.save') }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>
