<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

const props = defineProps<{ listing: Listing }>()

const emit = defineEmits<{ close: [], sold: [] }>()

const { t } = useI18n()

const listingStore = useListingStore()

const finalSalePrice = ref<number | ''>('')
const isSubmitting = ref(false)

async function handleConfirm(): Promise<void> {
  isSubmitting.value = true
  try {
    await listingStore.markListingSold(props.listing.id, {
      final_sale_price: finalSalePrice.value === '' ? undefined : Number(finalSalePrice.value),
    })
    emit('sold')
  } catch {
    // ошибка уже сохранена в listingStore.error и показана в форме
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :title="t('listingDetails.markSoldModalTitle')" @close="emit('close')">
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground" for="final-sale-price">
          {{ t('listingDetails.finalPriceLabel') }}
        </label>
        <input
          id="final-sale-price"
          v-model.number="finalSalePrice"
          type="number"
          min="0"
          step="0.01"
          :placeholder="String(listing.sale_price)"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p class="mt-1 text-xs text-muted-foreground">{{ t('listingDetails.finalPriceHint') }}</p>
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
        :disabled="isSubmitting"
        class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        @click="handleConfirm"
      >
        {{ t('listingDetails.confirmMarkSold') }}
      </button>
    </template>
  </BaseModal>
</template>
