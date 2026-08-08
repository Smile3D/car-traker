<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useForm, useField } from 'vee-validate'
import type { CarCreateInput, FuelType } from '~/types/cars'

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const validators = createValidators(t)

const carsStore = useCarStore()

const { meta, handleSubmit } = useForm()

const { value: brand, errorMessage: brandError } = useField<string>('brand', validators.required, { initialValue: '' })
const { value: model, errorMessage: modelError } = useField<string>('model', validators.required, { initialValue: '' })
const { value: year, errorMessage: yearError } = useField<string>('year', validators.numericString, { initialValue: '' })
const { value: mileage, errorMessage: mileageError } = useField<string>('mileage', validators.numericString, { initialValue: '' })
const { value: vin, errorMessage: vinError } = useField<string>('vin', validators.required, { initialValue: '' })
const { value: fuelType, errorMessage: fuelTypeError } = useField<FuelType>('fuel_type', validators.required, { initialValue: 'petrol' })

const addCar = handleSubmit(async (values) => {
  try {
    await carsStore.createCar(values as CarCreateInput)
    emit('close')
  } catch {
    // ошибка уже сохранена в carsStore.error и показана в форме
  }
})
</script>

<template>
  <BaseModal :title="t('carForm.addTitle')" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="addCar">
      <div>
        <label class="block text-sm font-medium text-foreground" for="brand">{{ t('carForm.brandLabel') }} <RequiredMark /></label>
        <input
          id="brand"
          v-model="brand"
          type="text"
          aria-required="true"
          :aria-invalid="!!brandError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="brandError" class="mt-1 text-xs text-destructive">{{ brandError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="model">{{ t('carForm.modelLabel') }} <RequiredMark /></label>
        <input
          id="model"
          v-model="model"
          type="text"
          aria-required="true"
          :aria-invalid="!!modelError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="modelError" class="mt-1 text-xs text-destructive">{{ modelError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="year">{{ t('carForm.yearLabel') }} <RequiredMark /></label>
        <input
          id="year"
          v-model="year"
          type="text"
          inputmode="numeric"
          aria-required="true"
          :aria-invalid="!!yearError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="yearError" class="mt-1 text-xs text-destructive">{{ yearError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="mileage">{{ t('carForm.mileageLabel') }} <RequiredMark /></label>
        <input
          id="mileage"
          v-model="mileage"
          type="text"
          inputmode="numeric"
          aria-required="true"
          :aria-invalid="!!mileageError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="mileageError" class="mt-1 text-xs text-destructive">{{ mileageError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="vin">{{ t('common.vin') }} <RequiredMark /></label>
        <input
          id="vin"
          v-model="vin"
          type="text"
          aria-required="true"
          :aria-invalid="!!vinError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="vinError" class="mt-1 text-xs text-destructive">{{ vinError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="fuel-type">{{ t('carForm.fuelTypeLabel') }} <RequiredMark /></label>
        <select
          id="fuel-type"
          v-model="fuelType"
          aria-required="true"
          :aria-invalid="!!fuelTypeError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="petrol">{{ t('carForm.fuelTypePetrol') }}</option>
          <option value="diesel">{{ t('carForm.fuelTypeDiesel') }}</option>
          <option value="gas">{{ t('carForm.fuelTypeGas') }}</option>
          <option value="gas_petrol">{{ t('carForm.fuelTypeGasPetrol') }}</option>
        </select>
        <p v-if="fuelTypeError" class="mt-1 text-xs text-destructive">{{ fuelTypeError }}</p>
      </div>

      <!-- ErrorAlert -->
      <div
        v-if="carsStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ carsStore.error }}</span>
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
          :disabled="carsStore.isLoading || !meta.valid"
          class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ carsStore.isLoading ? t('common.buttons.adding') : t('common.buttons.add') }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>
