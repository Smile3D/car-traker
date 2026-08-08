<script setup lang="ts">
import { PhotoIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type { Receipt } from '~/types/receipts'

const props = defineProps<{
  carId: number
  receipt: Receipt
}>()

const emit = defineEmits<{ open: [imageUrl: string], delete: [] }>()

const { t, d } = useI18n()

const receiptStore = useReceiptStore()

const imageUrl = ref<string | null>(null)
const hasLoadFailed = ref(false)

const linkLabel = computed<string | null>(() => getReceiptLinkLabel(props.receipt, t, d))

onMounted(async () => {
  try {
    imageUrl.value = await receiptStore.fetchReceiptImageUrl(props.carId, props.receipt.id)
  } catch {
    hasLoadFailed.value = true
  }
})

onUnmounted(() => {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
  }
})
</script>

<template>
  <div class="group relative overflow-hidden rounded-lg border border-border bg-surface">
    <button
      type="button"
      class="flex aspect-square w-full items-center justify-center overflow-hidden bg-muted disabled:cursor-default"
      :disabled="!imageUrl"
      @click="imageUrl && emit('open', imageUrl)"
    >
      <img
        v-if="imageUrl"
        :src="imageUrl"
        class="size-full object-cover transition-transform group-hover:scale-105"
        :alt="receipt.description || ''"
      >
      <PhotoIcon v-else class="size-8 text-muted-foreground" />
    </button>

    <button
      type="button"
      class="absolute right-2 top-2 flex size-7 items-center justify-center rounded-md bg-slate-900/60 text-white opacity-0 transition-opacity hover:bg-destructive group-hover:opacity-100"
      :aria-label="t('common.buttons.delete')"
      @click="emit('delete')"
    >
      <TrashIcon class="size-4" />
    </button>

    <div v-if="receipt.description || linkLabel" class="space-y-0.5 border-t border-border px-2 py-1.5">
      <p v-if="receipt.description" class="truncate text-xs text-muted-foreground">{{ receipt.description }}</p>
      <p v-if="linkLabel" class="truncate text-xs font-medium text-primary">{{ linkLabel }}</p>
    </div>
  </div>
</template>
