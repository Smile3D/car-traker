<script setup lang="ts">
const MAX_VISIBLE_OPTIONS = 50
const BLUR_CLOSE_DELAY_MS = 150

const props = withDefaults(defineProps<{
  modelValue: string
  options: string[]
  id?: string
  placeholder?: string
  disabled?: boolean
  isLoading?: boolean
  loadingLabel?: string
  ariaInvalid?: boolean
  allowManualEntry?: boolean
  manualEntryLabel?: string
  noResultsLabel?: string
}>(), {
  allowManualEntry: true,
})

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { t } = useI18n()

const isOpen = ref(false)
const searchQuery = ref(props.modelValue)
const isManualMode = ref(false)

watch(() => props.modelValue, (newValue) => {
  if (!isManualMode.value) {
    searchQuery.value = newValue
  }
})

const filteredOptions = computed<string[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const matches = query ? props.options.filter((option) => option.toLowerCase().includes(query)) : props.options
  return matches.slice(0, MAX_VISIBLE_OPTIONS)
})

function handleFocus(): void {
  if (props.disabled) {
    return
  }
  isOpen.value = true
}

function handleBlur(): void {
  window.setTimeout(() => {
    isOpen.value = false
    searchQuery.value = props.modelValue
  }, BLUR_CLOSE_DELAY_MS)
}

function selectOption(option: string): void {
  searchQuery.value = option
  emit('update:modelValue', option)
  isOpen.value = false
}

function enterManualMode(): void {
  isManualMode.value = true
  isOpen.value = false
  emit('update:modelValue', '')
}

function exitManualMode(): void {
  isManualMode.value = false
  searchQuery.value = props.modelValue
}

function handleManualInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="relative">
    <template v-if="!isManualMode">
      <input
        :id="id"
        v-model="searchQuery"
        type="text"
        autocomplete="off"
        :disabled="disabled || isLoading"
        :placeholder="isLoading ? (loadingLabel ?? t('ui.searchableSelect.loading')) : placeholder"
        :aria-invalid="ariaInvalid"
        class="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
        @focus="handleFocus"
        @blur="handleBlur"
        @input="isOpen = true"
      >

      <div
        v-if="isOpen"
        class="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-border bg-surface shadow-elevated"
      >
        <button
          v-for="option in filteredOptions"
          :key="option"
          type="button"
          class="block w-full px-3 py-2 text-left text-sm text-foreground hover:bg-muted"
          @mousedown.prevent="selectOption(option)"
        >
          {{ option }}
        </button>

        <p v-if="filteredOptions.length === 0" class="px-3 py-2 text-sm text-muted-foreground">
          {{ noResultsLabel ?? t('ui.searchableSelect.noResults') }}
        </p>

        <button
          v-if="allowManualEntry"
          type="button"
          class="block w-full border-t border-border px-3 py-2 text-left text-sm font-medium text-primary hover:bg-muted"
          @mousedown.prevent="enterManualMode"
        >
          {{ manualEntryLabel ?? t('ui.searchableSelect.manualEntry') }}
        </button>
      </div>
    </template>

    <template v-else>
      <input
        :id="id"
        type="text"
        :value="modelValue"
        :placeholder="placeholder"
        :aria-invalid="ariaInvalid"
        class="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        @input="handleManualInput"
      >
      <button
        type="button"
        class="mt-1 text-xs font-medium text-primary hover:underline"
        @click="exitManualMode"
      >
        {{ t('ui.searchableSelect.backToList') }}
      </button>
    </template>
  </div>
</template>
