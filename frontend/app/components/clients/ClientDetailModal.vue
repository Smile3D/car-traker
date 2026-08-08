<script setup lang="ts">
import { PencilSquareIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type { Client, ClientFormValues } from '~/types/clients'

const props = defineProps<{ client: Client }>()

const emit = defineEmits<{ close: [], deleted: [] }>()

const { t } = useI18n()

const clientStore = useClientStore()

const isEditMode = ref(false)
const isDeleteConfirmOpen = ref(false)

async function handleSubmit(values: ClientFormValues): Promise<void> {
  try {
    await clientStore.updateClient(props.client.id, {
      name: values.name,
      phone: values.phone,
      email: values.email,
      social_media: values.social_media,
      notes: values.notes,
      employee_id: values.employee_id,
      lead_source: values.lead_source,
    })
    isEditMode.value = false
  } catch {
    // ошибка уже сохранена в clientStore.error и показана в форме
  }
}

async function handleDeleteConfirm(): Promise<void> {
  await clientStore.deleteClient(props.client.id)
  emit('deleted')
}
</script>

<template>
  <BaseModal :title="client.name" @close="emit('close')">
    <div class="space-y-4">
      <ClientDetailsReadOnly v-if="!isEditMode" :client="client" />
      <ClientForm
        v-else
        :initial-client="client"
        show-notes-field
        show-employee-field
        :submit-label="t('common.buttons.save')"
        :submitting-label="t('common.buttons.saving')"
        show-cancel-button
        :cancel-label="t('common.buttons.cancel')"
        @submit="handleSubmit"
        @cancel="isEditMode = false"
      />

      <div class="flex items-center justify-between border-t border-border pt-4">
        <button
          v-if="!isEditMode"
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isEditMode = true"
        >
          <PencilSquareIcon class="size-4" />
          {{ t('common.buttons.edit') }}
        </button>
        <span v-else />

        <button
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          @click="isDeleteConfirmOpen = true"
        >
          <TrashIcon class="size-4" />
          {{ t('crm.clients.form.deleteButton') }}
        </button>
      </div>
    </div>

    <ConfirmDialog
      v-if="isDeleteConfirmOpen"
      :title="t('crm.clients.form.confirmDeleteTitle')"
      :message="t('crm.clients.form.confirmDeleteMessage')"
      @confirm="handleDeleteConfirm"
      @cancel="isDeleteConfirmOpen = false"
    />
  </BaseModal>
</template>
