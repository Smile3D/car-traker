<script setup lang="ts">
import type { Receipt } from '~/types/receipts'

const props = defineProps<{
  imageUrl: string
  receipt: Receipt
}>()

const emit = defineEmits<{ close: [] }>()

const { t, d } = useI18n()

const linkLabel = computed<string | null>(() => getReceiptLinkLabel(props.receipt, t, d))
</script>

<template>
  <BaseModal :title="receipt.description || t('receipts.previewAlt')" max-width="lg" @close="emit('close')">
    <img :src="imageUrl" class="max-h-[70vh] w-full rounded-md object-contain" :alt="receipt.description || ''">
    <p v-if="linkLabel" class="mt-3 text-sm font-medium text-primary">{{ linkLabel }}</p>
  </BaseModal>
</template>
