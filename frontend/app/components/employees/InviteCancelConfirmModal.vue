<script setup lang="ts">
const emit = defineEmits<{ confirm: [reason: string | undefined], cancel: [] }>()

const { t } = useI18n()

const reason = ref('')

function handleConfirm(): void {
  emit('confirm', reason.value.trim() || undefined)
}
</script>

<template>
  <BaseModal :title="t('crm.employees.invites.cancelConfirmTitle')" @close="emit('cancel')">
    <div class="space-y-4">
      <p class="text-sm text-foreground">{{ t('crm.employees.invites.cancelConfirmMessage') }}</p>

      <div>
        <label class="block text-sm font-medium text-foreground" for="invite-cancel-reason">
          {{ t('crm.employees.invites.cancelReasonLabel') }}
        </label>
        <textarea
          id="invite-cancel-reason"
          v-model="reason"
          rows="3"
          :placeholder="t('crm.employees.invites.cancelReasonPlaceholder')"
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
        {{ t('crm.employees.invites.cancelGoBackButton') }}
      </button>
      <button
        type="button"
        class="flex-1 rounded-md bg-destructive px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-destructive-hover"
        @click="handleConfirm"
      >
        {{ t('crm.employees.invites.cancelConfirmButton') }}
      </button>
    </template>
  </BaseModal>
</template>
