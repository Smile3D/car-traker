<script setup lang="ts">
import { CheckIcon, ClipboardIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import type { EmployeeInviteCreateResult } from '~/types/employeeInvites'

// existingToken: reopening the link view for an invite that's already
// active (created earlier), skipping the create-form step entirely — same
// modal, same link+copy UI, just no new invite gets generated.
const props = defineProps<{ existingToken?: string }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

const employeeInviteStore = useEmployeeInviteStore()
const positionStore = usePositionStore()

const email = ref('')
const positionId = ref<number | ''>('')
const isSubmitting = ref(false)

const generatedInvite = ref<EmployeeInviteCreateResult | null>(null)
const isShowingLink = computed<boolean>(() => Boolean(props.existingToken) || generatedInvite.value !== null)
const inviteLink = computed<string>(() => {
  const token = props.existingToken ?? generatedInvite.value?.token
  return token ? `${window.location.origin}/register?invite=${token}` : ''
})

const copyFeedback = ref(false)

async function handleGenerate(): Promise<void> {
  isSubmitting.value = true
  try {
    generatedInvite.value = await employeeInviteStore.createInvite({
      email: email.value.trim() || undefined,
      position_id: positionId.value === '' ? undefined : Number(positionId.value),
    })
  } catch {
    // ошибка уже сохранена в employeeInviteStore.error и показана ниже
  } finally {
    isSubmitting.value = false
  }
}

async function copyLink(): Promise<void> {
  await navigator.clipboard.writeText(inviteLink.value)
  copyFeedback.value = true
  setTimeout(() => { copyFeedback.value = false }, 2000)
}
</script>

<template>
  <BaseModal :title="t('crm.employees.invites.modalTitle')" @close="emit('close')">
    <div v-if="!isShowingLink" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground" for="invite-email">
          {{ t('crm.employees.invites.emailLabel') }}
        </label>
        <input
          id="invite-email"
          v-model="email"
          type="email"
          :placeholder="t('crm.employees.invites.emailPlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p class="mt-1 text-xs text-muted-foreground">{{ t('crm.employees.invites.emailHint') }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="invite-position">
          {{ t('crm.employees.form.positionLabel') }}
        </label>
        <select
          id="invite-position"
          v-model="positionId"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">{{ t('crm.employees.form.positionNotAssigned') }}</option>
          <option v-for="position in positionStore.positions" :key="position.id" :value="position.id">
            {{ position.name }}
          </option>
        </select>
      </div>

      <div
        v-if="employeeInviteStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ employeeInviteStore.error }}</span>
      </div>

      <div class="flex justify-end gap-2 border-t border-border pt-4">
        <button
          type="button"
          class="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          @click="emit('close')"
        >
          {{ t('common.buttons.cancel') }}
        </button>
        <button
          type="button"
          :disabled="isSubmitting"
          class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          @click="handleGenerate"
        >
          {{ isSubmitting ? t('crm.employees.invites.generating') : t('crm.employees.invites.generateButton') }}
        </button>
      </div>
    </div>

    <div v-else class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-foreground">{{ t('crm.employees.invites.linkLabel') }}</label>
        <div class="mt-1.5 flex items-center gap-2">
          <input
            type="text"
            readonly
            :value="inviteLink"
            class="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            @focus="($event.target as HTMLInputElement).select()"
          >
          <button
            type="button"
            class="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            @click="copyLink"
          >
            <CheckIcon v-if="copyFeedback" class="size-4 text-success" />
            <ClipboardIcon v-else class="size-4" />
            {{ copyFeedback ? t('crm.employees.invites.copiedFeedback') : t('crm.employees.invites.copyButton') }}
          </button>
        </div>
      </div>

      <p class="text-sm text-muted-foreground">{{ t('crm.employees.invites.shareHint') }}</p>

      <div class="flex justify-end border-t border-border pt-4">
        <button
          type="button"
          class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
          @click="emit('close')"
        >
          {{ t('common.buttons.close') }}
        </button>
      </div>
    </div>
  </BaseModal>
</template>
