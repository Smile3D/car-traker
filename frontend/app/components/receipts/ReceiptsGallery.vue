<script setup lang="ts">
import { PhotoIcon } from '@heroicons/vue/24/outline'
import type { Receipt } from '~/types/receipts'

const props = defineProps<{ carId: number }>()

const { t } = useI18n()

const receiptStore = useReceiptStore()

await receiptStore.fetchReceipts(props.carId)

const lightboxImageUrl = ref<string | null>(null)
const lightboxReceipt = ref<Receipt | null>(null)
const receiptPendingDeletion = ref<Receipt | null>(null)

function openLightbox(imageUrl: string, receipt: Receipt): void {
  lightboxImageUrl.value = imageUrl
  lightboxReceipt.value = receipt
}

async function handleConfirmDelete(): Promise<void> {
  if (!receiptPendingDeletion.value) {
    return
  }

  await receiptStore.deleteReceipt(props.carId, receiptPendingDeletion.value.id)
  receiptPendingDeletion.value = null
}
</script>

<template>
  <div class="space-y-4">
    <!-- ReceiptsEmptyState -->
    <div
      v-if="receiptStore.receipts.length === 0"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong px-6 py-12 text-center"
    >
      <PhotoIcon class="size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ t('receipts.emptyState') }}</p>
    </div>

    <!-- ReceiptsGrid -->
    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      <ReceiptThumbnail
        v-for="receipt in receiptStore.receipts"
        :key="receipt.id"
        :car-id="carId"
        :receipt="receipt"
        @open="openLightbox($event, receipt)"
        @delete="receiptPendingDeletion = receipt"
      />
    </div>

    <ReceiptLightboxModal
      v-if="lightboxImageUrl && lightboxReceipt"
      :image-url="lightboxImageUrl"
      :receipt="lightboxReceipt"
      @close="lightboxImageUrl = null"
    />

    <ConfirmDialog
      v-if="receiptPendingDeletion"
      :title="t('receipts.deleteConfirmTitle')"
      :message="t('receipts.deleteConfirmMessage')"
      @confirm="handleConfirmDelete"
      @cancel="receiptPendingDeletion = null"
    />
  </div>
</template>
