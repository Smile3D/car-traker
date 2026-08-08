<script setup lang="ts">
import { XMarkIcon, PlusIcon } from '@heroicons/vue/24/outline'
import type { ServiceRecordItemInput } from '~/types/serviceRecords'

const items = defineModel<ServiceRecordItemInput[]>({ required: true })

const { t } = useI18n()

const touchedIndexes = ref<Set<number>>(new Set())

function addItem(): void {
  items.value = [...items.value, { name: '', price: 0 }]
}

function removeItem(index: number): void {
  items.value = items.value.filter((_, itemIndex) => itemIndex !== index)
  touchedIndexes.value.delete(index)
}

function markTouched(index: number): void {
  touchedIndexes.value.add(index)
}

function isNameInvalid(index: number, name: string): boolean {
  return touchedIndexes.value.has(index) && name.trim() === ''
}

function isPriceInvalid(index: number, price: number): boolean {
  return touchedIndexes.value.has(index) && (price === null || Number.isNaN(price) || price < 0)
}
</script>

<template>
  <div class="space-y-2">
    <label class="block text-sm font-medium text-foreground">{{ t('serviceRecordItems.label') }} <RequiredMark /></label>

    <!-- ServiceRecordItemRow -->
    <div
      v-for="(item, index) in items"
      :key="index"
      class="flex gap-2"
    >
      <div class="flex-1">
        <input
          v-model="item.name"
          type="text"
          :placeholder="t('serviceRecordItems.namePlaceholder')"
          aria-required="true"
          :aria-invalid="isNameInvalid(index, item.name)"
          class="w-full rounded-md border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          :class="isNameInvalid(index, item.name) ? 'border-destructive' : 'border-border'"
          @blur="markTouched(index)"
        >
        <p v-if="isNameInvalid(index, item.name)" class="mt-1 text-xs text-destructive">{{ t('validation.required') }}</p>
      </div>

      <div class="w-28">
        <input
          v-model.number="item.price"
          type="number"
          min="0"
          step="0.01"
          :placeholder="t('serviceRecordItems.pricePlaceholder')"
          aria-required="true"
          :aria-invalid="isPriceInvalid(index, item.price)"
          class="w-full rounded-md border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          :class="isPriceInvalid(index, item.price) ? 'border-destructive' : 'border-border'"
          @blur="markTouched(index)"
        >
        <p v-if="isPriceInvalid(index, item.price)" class="mt-1 text-xs text-destructive">{{ t('validation.nonNegativeNumber') }}</p>
      </div>

      <button
        type="button"
        class="flex h-fit items-center justify-center rounded-md border border-destructive/30 px-2 py-2 text-destructive hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-30"
        :disabled="items.length === 1"
        :aria-label="t('common.buttons.delete')"
        @click="removeItem(index)"
      >
        <XMarkIcon class="size-4" />
      </button>
    </div>

    <button
      type="button"
      class="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
      @click="addItem"
    >
      <PlusIcon class="size-4" />
      {{ t('serviceRecordItems.addItem') }}
    </button>
  </div>
</template>
