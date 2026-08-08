<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

const props = defineProps<{ listing: Listing }>()

const emit = defineEmits<{ close: [], markedOnService: [] }>()

const { t } = useI18n()

const listingStore = useListingStore()

const today = new Date().toISOString().slice(0, 10)

const serviceNote = ref<string>('')
const serviceStartDate = ref<string>(today)
const serviceExpectedEndDate = ref<string>('')
const isSubmitting = ref(false)

const expectedEndBeforeStartError = computed<string | null>(() =>
  serviceExpectedEndDate.value && serviceExpectedEndDate.value < serviceStartDate.value
    ? t('listingDetails.serviceExpectedEndBeforeStartError')
    : null
)

const canSubmit = computed<boolean>(() => !!serviceStartDate.value && !expectedEndBeforeStartError.value)

async function handleConfirm(): Promise<void> {
  if (!canSubmit.value) {
    return
  }

  isSubmitting.value = true
  try {
    await listingStore.markListingOnService(props.listing.id, {
      service_note: serviceNote.value || undefined,
      service_start_date: serviceStartDate.value,
      service_expected_end_date: serviceExpectedEndDate.value || undefined,
    })
    emit('markedOnService')
  } catch {
    // ошибка уже сохранена в listingStore.error и показана в форме
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :title="t('listingDetails.markOnServiceModalTitle')" @close="emit('close')">
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground" for="service-start-date">
          {{ t('listingDetails.serviceStartDateLabel') }} <RequiredMark />
        </label>
        <input
          id="service-start-date"
          v-model="serviceStartDate"
          type="date"
          aria-required="true"
          :aria-invalid="!!expectedEndBeforeStartError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="service-expected-end-date">
          {{ t('listingDetails.serviceExpectedEndDateLabel') }}
        </label>
        <input
          id="service-expected-end-date"
          v-model="serviceExpectedEndDate"
          type="date"
          :aria-invalid="!!expectedEndBeforeStartError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="expectedEndBeforeStartError" class="mt-1 text-xs text-destructive">{{ expectedEndBeforeStartError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="service-note">
          {{ t('listingDetails.serviceNoteLabel') }}
        </label>
        <textarea
          id="service-note"
          v-model="serviceNote"
          rows="3"
          :placeholder="t('listingDetails.serviceNotePlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      <!-- ErrorAlert -->
      <div
        v-if="listingStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ listingStore.error }}</span>
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="flex-1 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        @click="emit('close')"
      >
        {{ t('common.buttons.cancel') }}
      </button>
      <button
        type="button"
        :disabled="isSubmitting || !canSubmit"
        class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        @click="handleConfirm"
      >
        {{ t('common.buttons.save') }}
      </button>
    </template>
  </BaseModal>
</template>
