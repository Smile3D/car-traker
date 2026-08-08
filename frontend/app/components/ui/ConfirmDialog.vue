<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

defineProps<{
  title: string
  message: string
  confirmLabel?: string
}>()

const emit = defineEmits<{ confirm: [], cancel: [] }>()

const { t } = useI18n()
</script>

<template>
  <BaseModal :title="title" @close="emit('cancel')">
    <div class="flex items-start gap-3">
      <ExclamationTriangleIcon class="mt-0.5 size-5 shrink-0 text-destructive" />
      <p class="text-sm text-foreground">{{ message }}</p>
    </div>

    <template #footer>
      <button
        type="button"
        class="flex-1 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        @click="emit('cancel')"
      >
        {{ t('common.buttons.cancel') }}
      </button>
      <button
        type="button"
        class="flex-1 rounded-md bg-destructive px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-destructive-hover"
        @click="emit('confirm')"
      >
        {{ confirmLabel ?? t('common.buttons.delete') }}
      </button>
    </template>
  </BaseModal>
</template>
