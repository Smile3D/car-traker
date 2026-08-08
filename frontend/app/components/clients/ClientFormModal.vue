<script setup lang="ts">
import type { ClientFormValues } from '~/types/clients'
import type { ClientType } from '~/utils/clientStages'

const props = defineProps<{ clientType: ClientType }>()

const emit = defineEmits<{ close: [], created: [] }>()

const { t } = useI18n()

const clientStore = useClientStore()

async function handleSubmit(values: ClientFormValues): Promise<void> {
  try {
    await clientStore.createClient({
      listing_id: values.listing_id!,
      client_type: props.clientType,
      name: values.name,
      phone: values.phone,
      email: values.email,
      social_media: values.social_media,
      lead_source: values.lead_source,
    })
    emit('created')
  } catch {
    // ошибка уже сохранена в clientStore.error и показана в форме
  }
}
</script>

<template>
  <BaseModal :title="t('crm.clients.form.addTitle')" @close="emit('close')">
    <ClientForm
      show-listing-selector
      :submit-label="t('crm.clients.form.submitLabel')"
      :submitting-label="t('crm.clients.form.submittingLabel')"
      show-cancel-button
      :cancel-label="t('common.buttons.cancel')"
      @submit="handleSubmit"
      @cancel="emit('close')"
    />
  </BaseModal>
</template>
