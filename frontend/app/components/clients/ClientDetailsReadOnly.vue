<script setup lang="ts">
import type { Client } from '~/types/clients'
import type { Listing } from '~/types/listings'
import { getLeadSourceLabelKey } from '~/utils/clientOptions'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ client: Client }>()

const { t } = useI18n()

const listingStore = useListingStore()
const clientStageStore = useClientStageStore()

const linkedListing = computed<Listing | undefined>(() =>
  listingStore.listings.find((listing) => listing.id === props.client.listing_id)
)

const stageName = computed<string | undefined>(() =>
  clientStageStore.stages.find((stage) => stage.id === props.client.stage_id)?.name
)

const assignedEmployeeName = computed<string | undefined>(() => getEmployeeDisplayName(props.client.employee))
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <span v-if="stageName" class="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
        {{ stageName }}
      </span>
      <NuxtLink
        v-if="linkedListing"
        :to="`/crm/inventory/${linkedListing.id}`"
        class="text-xs font-medium text-primary hover:underline"
      >
        {{ linkedListing.brand }} {{ linkedListing.model }}, {{ linkedListing.year }}
      </NuxtLink>
    </div>

    <dl class="grid grid-cols-1 gap-4">
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.nameLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ client.name }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.phoneLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ client.phone }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.emailLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ client.email || '—' }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.socialMediaLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ client.social_media || '—' }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.employeeLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ assignedEmployeeName || t('crm.clients.form.employeeNotAssigned') }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.leadSourceLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ client.lead_source ? t(getLeadSourceLabelKey(client.lead_source)) : t('crm.clients.form.leadSourceNotSpecified') }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.notesLabel') }}</dt>
        <dd class="mt-0.5 whitespace-pre-line text-sm text-foreground">{{ client.notes || '—' }}</dd>
      </div>
    </dl>
  </div>
</template>
