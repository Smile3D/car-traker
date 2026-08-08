<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const emit = defineEmits<{ confirm: [reason: string | undefined], cancel: [] }>()

const { t } = useI18n()

const reason = ref('')

function handleConfirm(): void {
  emit('confirm', reason.value.trim() || undefined)
}
</script>

<template>
  <BaseModal :title="t('listingDetails.deleteBuyerConfirmTitle')" @close="emit('cancel')">
    <div class="space-y-4">
      <div class="flex items-start gap-3">
        <ExclamationTriangleIcon class="mt-0.5 size-5 shrink-0 text-destructive" />
        <p class="text-sm text-foreground">{{ t('listingDetails.deleteBuyerConfirmMessage') }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="buyer-delete-reason">
          {{ t('listingDetails.deleteBuyerReasonLabel') }}
        </label>
        <textarea
          id="buyer-delete-reason"
          v-model="reason"
          rows="3"
          :placeholder="t('listingDetails.deleteBuyerReasonPlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
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
        @click="handleConfirm"
      >
        {{ t('common.buttons.delete') }}
      </button>
    </template>
  </BaseModal>
</template>
