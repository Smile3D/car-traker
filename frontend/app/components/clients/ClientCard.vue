<script setup lang="ts">
import { AtSymbolIcon, EnvelopeIcon, PhoneIcon, UserIcon } from '@heroicons/vue/24/outline'
import type { Client } from '~/types/clients'
import type { Listing } from '~/types/listings'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ client: Client }>()

const { t } = useI18n()

const listingStore = useListingStore()

const linkedListing = computed<Listing | undefined>(() =>
  listingStore.listings.find((listing) => listing.id === props.client.listing_id)
)

const assignedEmployeeName = computed<string | undefined>(() => getEmployeeDisplayName(props.client.employee))
</script>

<template>
  <div class="cursor-pointer select-none space-y-1.5 rounded-md border border-border bg-surface p-3 shadow-card transition-colors hover:border-primary/40">
    <p class="text-sm font-medium text-foreground">{{ client.name }}</p>

    <p class="flex items-center gap-1.5 text-xs text-muted-foreground">
      <PhoneIcon class="size-3.5 shrink-0" />
      {{ client.phone }}
    </p>

    <p v-if="assignedEmployeeName" class="flex items-center gap-1.5 text-xs text-muted-foreground">
      <UserIcon class="size-3.5 shrink-0" />
      {{ t('crm.clients.card.responsibleEmployee', { name: assignedEmployeeName }) }}
    </p>

    <div v-if="linkedListing" class="flex items-center gap-2">
      <ListingCoverThumbnail :listing-id="linkedListing.id" size="sm" />
      <NuxtLink
        :to="`/crm/inventory/${linkedListing.id}`"
        class="text-xs font-medium text-primary hover:underline"
        @click.stop
      >
        {{ linkedListing.brand }} {{ linkedListing.model }}, {{ linkedListing.year }}
      </NuxtLink>
    </div>

    <div v-if="client.email || client.social_media" class="flex items-center gap-2 pt-0.5 text-muted-foreground">
      <EnvelopeIcon v-if="client.email" class="size-3.5" :title="client.email" />
      <AtSymbolIcon v-if="client.social_media" class="size-3.5" :title="client.social_media" />
    </div>
  </div>
</template>
