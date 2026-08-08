<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useForm, useField } from 'vee-validate'
import type { ServiceRecord, ServiceRecordItemInput } from '~/types/serviceRecords'

const props = defineProps<{ carId: number, serviceRecord: ServiceRecord }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const validators = createValidators(t)

const serviceRecordStore = useServiceRecordStore()
const carsStore = useCarStore()

const { meta, handleSubmit } = useForm()

const { value: serviceDate, errorMessage: serviceDateError } = useField<string>('service_date', validators.required, { initialValue: props.serviceRecord.service_date })
const { value: mileage, errorMessage: mileageError } = useField<number | ''>('mileage', validators.nonNegativeNumber, { initialValue: props.serviceRecord.mileage })

const items = ref<ServiceRecordItemInput[]>(props.serviceRecord.items.map((item) => ({ name: item.name, price: item.price })))
const itemsValid = computed<boolean>(() => areServiceRecordItemsValid(items.value))

const mileageLabel = computed<string>(() => props.serviceRecord.record_type === 'repair' ? t('serviceRecordForm.mileageLabelRepair') : t('serviceRecordForm.mileageLabelMaintenance'))

const saveServiceRecord = handleSubmit(async () => {
  try {
    await serviceRecordStore.updateServiceRecord(props.carId, props.serviceRecord.id, {
      service_date: serviceDate.value,
      mileage: Number(mileage.value),
      items: items.value,
    })
    await carsStore.fetchCarById(props.carId)
    emit('close')
  } catch {
    // ошибка уже сохранена в serviceRecordStore.error и показана в форме
  }
})
</script>

<template>
  <BaseModal :title="t('serviceRecordForm.editTitle')" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="saveServiceRecord">
      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-service-date">{{ t('serviceRecordForm.dateLabel') }} <RequiredMark /></label>
        <input
          id="edit-service-date"
          v-model="serviceDate"
          type="date"
          aria-required="true"
          :aria-invalid="!!serviceDateError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="serviceDateError" class="mt-1 text-xs text-destructive">{{ serviceDateError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="edit-mileage">{{ mileageLabel }} <RequiredMark /></label>
        <input
          id="edit-mileage"
          v-model.number="mileage"
          type="number"
          min="0"
          step="1"
          aria-required="true"
          :aria-invalid="!!mileageError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="mileageError" class="mt-1 text-xs text-destructive">{{ mileageError }}</p>
      </div>

      <ServiceRecordItemsFields v-model="items" />

      <!-- ErrorAlert -->
      <div
        v-if="serviceRecordStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ serviceRecordStore.error }}</span>
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
          :disabled="serviceRecordStore.isLoading || !meta.valid || !itemsValid"
          class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ serviceRecordStore.isLoading ? t('common.buttons.saving') : t('common.buttons.save') }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>
