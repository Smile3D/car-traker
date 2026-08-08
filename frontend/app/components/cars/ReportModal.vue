<script setup lang="ts">
import { CheckCircleIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{ initialText: string }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

const reportText = ref(props.initialText)
const isCopied = ref(false)

async function handleCopyClick(): Promise<void> {
  await navigator.clipboard.writeText(reportText.value)
  isCopied.value = true
  setTimeout(() => {
    isCopied.value = false
  }, 2000)
}
</script>

<template>
  <BaseModal :title="t('report.modalTitle')" max-width="lg" @close="emit('close')">
    <textarea
      v-model="reportText"
      rows="14"
      class="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
    />

    <p v-if="isCopied" class="mt-2 flex items-center gap-1.5 text-sm font-medium text-success">
      <CheckCircleIcon class="size-4" />
      {{ t('report.copied') }}
    </p>

    <div class="mt-4 flex gap-2 border-t border-border pt-4">
      <button
        type="button"
        class="flex-1 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        @click="emit('close')"
      >
        {{ t('common.buttons.cancel') }}
      </button>
      <button
        type="button"
        class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
        @click="handleCopyClick"
      >
        {{ t('report.copy') }}
      </button>
    </div>
  </BaseModal>
</template>
