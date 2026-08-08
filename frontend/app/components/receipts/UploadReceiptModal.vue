<script setup lang="ts">
import { ExclamationTriangleIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import type { ServiceRecord } from '~/types/serviceRecords'
import type { FuelRefill } from '~/types/fuelRefills'

type ReceiptLinkMode = 'none' | 'service_record' | 'fuel_refill'

const props = defineProps<{ carId: number }>()

const emit = defineEmits<{ close: [] }>()

const { t, n, d } = useI18n()

const receiptStore = useReceiptStore()
const serviceRecordStore = useServiceRecordStore()
const fuelRefillStore = useFuelRefillStore()

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const description = ref('')
const validationError = ref<string | null>(null)

const linkMode = ref<ReceiptLinkMode>('none')
const selectedServiceRecordId = ref<number | ''>('')
const selectedFuelRefillId = ref<number | ''>('')

watch(linkMode, () => {
  selectedServiceRecordId.value = ''
  selectedFuelRefillId.value = ''
})

function serviceRecordOptionLabel(record: ServiceRecord): string {
  const typeLabel = record.record_type === 'repair' ? t('charts.legend.repair') : t('charts.legend.maintenance')
  const itemNames = record.items.map((item) => item.name).join(', ')
  const datePart = `${d(new Date(record.service_date), 'short')} · ${n(record.mileage, 'decimal')} ${t('common.units.km')} · ${typeLabel}`
  return itemNames ? `${datePart} · ${itemNames}` : datePart
}

function fuelRefillOptionLabel(refill: FuelRefill): string {
  return `${d(new Date(refill.refill_date), 'short')} · ${n(refill.fuel_amount, 'decimal')} ${t('common.units.liters')} · ${n(refill.cost, 'currency')}`
}

function revokePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

function handleFileChange(fileChangeEvent: Event): void {
  const file = (fileChangeEvent.target as HTMLInputElement).files?.[0] ?? null
  validationError.value = null
  revokePreview()
  selectedFile.value = null

  if (!file) {
    return
  }

  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    validationError.value = t('receipts.errorInvalidType')
    return
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    validationError.value = t('receipts.errorTooLarge')
    return
  }

  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
}

const isSubmitting = ref(false)

async function handleSubmit(): Promise<void> {
  if (!selectedFile.value) {
    return
  }

  isSubmitting.value = true
  try {
    await receiptStore.uploadReceipt(props.carId, selectedFile.value, {
      description: description.value || undefined,
      serviceRecordId: linkMode.value === 'service_record' && selectedServiceRecordId.value !== ''
        ? Number(selectedServiceRecordId.value)
        : undefined,
      fuelRefillId: linkMode.value === 'fuel_refill' && selectedFuelRefillId.value !== ''
        ? Number(selectedFuelRefillId.value)
        : undefined,
    })
    emit('close')
  } catch {
    // ошибка уже сохранена в receiptStore.error и показана в форме
  } finally {
    isSubmitting.value = false
  }
}

onUnmounted(() => {
  revokePreview()
})
</script>

<template>
  <BaseModal :title="t('receipts.uploadTitle')" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="handleSubmit">
      <div>
        <label class="block text-sm font-medium text-foreground" for="receipt-file">
          {{ t('receipts.fileLabel') }} <RequiredMark />
        </label>

        <label
          for="receipt-file"
          class="mt-1.5 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border-strong px-4 py-6 text-center hover:bg-muted"
        >
          <img
            v-if="previewUrl"
            :src="previewUrl"
            class="max-h-40 rounded-md object-contain"
            :alt="t('receipts.previewAlt')"
          >
          <template v-else>
            <PhotoIcon class="size-8 text-muted-foreground" />
            <span class="text-sm text-muted-foreground">{{ t('receipts.chooseFile') }}</span>
          </template>
        </label>

        <input
          id="receipt-file"
          type="file"
          accept="image/*"
          aria-required="true"
          class="sr-only"
          @change="handleFileChange"
        >

        <p v-if="validationError" class="mt-1 text-xs text-destructive">{{ validationError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="receipt-description">
          {{ t('receipts.descriptionLabel') }}
        </label>
        <textarea
          id="receipt-description"
          v-model="description"
          rows="2"
          :placeholder="t('receipts.descriptionPlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="receipt-link-mode">
          {{ t('receipts.linkLabel') }}
        </label>
        <select
          id="receipt-link-mode"
          v-model="linkMode"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="none">{{ t('receipts.linkNone') }}</option>
          <option value="service_record">{{ t('receipts.linkServiceRecord') }}</option>
          <option value="fuel_refill">{{ t('receipts.linkFuelRefill') }}</option>
        </select>

        <select
          v-if="linkMode === 'service_record'"
          v-model="selectedServiceRecordId"
          class="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">—</option>
          <option v-for="record in serviceRecordStore.serviceRecords" :key="record.id" :value="record.id">
            {{ serviceRecordOptionLabel(record) }}
          </option>
        </select>

        <select
          v-if="linkMode === 'fuel_refill'"
          v-model="selectedFuelRefillId"
          class="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">—</option>
          <option v-for="refill in fuelRefillStore.fuelRefills" :key="refill.id" :value="refill.id">
            {{ fuelRefillOptionLabel(refill) }}
          </option>
        </select>
      </div>

      <!-- ErrorAlert -->
      <div
        v-if="receiptStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ receiptStore.error }}</span>
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
          :disabled="isSubmitting || !selectedFile"
          class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ isSubmitting ? t('receipts.uploading') : t('receipts.upload') }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>
