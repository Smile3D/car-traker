<script setup lang="ts">
import { PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'

defineProps<{
  label: string
  placeholder: string
  addButtonLabel: string
}>()

// Always at least one field in the UI, even if empty, so there's always a
// visible input to type a first link into — the remove button only shows
// once there's more than one.
const links = defineModel<string[]>({ default: () => [''] })

function addLink(): void {
  links.value.push('')
}

function removeLink(index: number): void {
  links.value.splice(index, 1)
}

const { t } = useI18n()
</script>

<template>
  <div>
    <label class="block text-sm font-medium text-foreground">{{ label }}</label>
    <div class="mt-1.5 space-y-2">
      <div v-for="(link, index) in links" :key="index" class="flex items-center gap-2">
        <input
          v-model="links[index]"
          type="text"
          :placeholder="placeholder"
          class="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <button
          v-if="links.length > 1"
          type="button"
          class="flex shrink-0 items-center justify-center rounded-md border border-border p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-destructive"
          :aria-label="t('common.buttons.delete')"
          @click="removeLink(index)"
        >
          <XMarkIcon class="size-4" />
        </button>
      </div>
    </div>
    <button
      type="button"
      class="mt-2 flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
      @click="addLink"
    >
      <PlusIcon class="size-4" />
      {{ addButtonLabel }}
    </button>
  </div>
</template>
