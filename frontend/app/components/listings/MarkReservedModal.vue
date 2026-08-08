<script setup lang="ts">
import { ExclamationTriangleIcon, MagnifyingGlassIcon, PlusIcon, UserGroupIcon } from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { Client, ClientFormValues } from '~/types/clients'
import type { Listing } from '~/types/listings'

const props = defineProps<{ listing: Listing }>()

const emit = defineEmits<{ close: [], reserved: [] }>()

const { t } = useI18n()

const listingStore = useListingStore()
const clientStore = useClientStore()

// If a buyer Client already exists for this listing (created earlier via
// this same modal, or via the standalone Clients page), reuse it instead of
// making the user pick again — a second buyer Client on the same listing
// would just 409 (one-buyer-per-listing DB constraint).
const existingBuyer = computed<Client | undefined>(() =>
  clientStore.clients.find((client) => client.listing_id === props.listing.id && client.client_type === 'buyer')
)

const selectedBuyer = ref<Client | undefined>(existingBuyer.value)

type PickerView = 'search' | 'create'
const pickerView = ref<PickerView>('search')

const searchQuery = ref('')

const filteredClients = computed<Client[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const sortedClients = [...clientStore.clients].sort((a, b) => b.created_at.localeCompare(a.created_at))
  if (!query) {
    return sortedClients.slice(0, 30)
  }
  return sortedClients.filter((client) =>
    client.name.toLowerCase().includes(query) || client.phone.toLowerCase().includes(query)
  ).slice(0, 30)
})

const isSavingBuyer = ref(false)
const buyerErrorMessage = ref('')

// Picking an existing client re-uses their contact info to create a NEW
// buyer Client scoped to THIS listing — every Client row is permanently
// scoped to exactly one listing (that's the existing data model, not
// something introduced here), so "select an existing client" can never mean
// literally re-pointing their old Client row at a different listing.
async function handlePickExisting(client: Client): Promise<void> {
  buyerErrorMessage.value = ''
  isSavingBuyer.value = true
  try {
    selectedBuyer.value = await clientStore.createClient({
      listing_id: props.listing.id,
      client_type: 'buyer',
      name: client.name,
      phone: client.phone,
      email: client.email || undefined,
      social_media: client.social_media || undefined,
    })
  } catch (error) {
    buyerErrorMessage.value = (error as ApiError).message
  } finally {
    isSavingBuyer.value = false
  }
}

async function handleCreateNewSubmit(values: ClientFormValues): Promise<void> {
  buyerErrorMessage.value = ''
  isSavingBuyer.value = true
  try {
    selectedBuyer.value = await clientStore.createClient({
      listing_id: props.listing.id,
      client_type: 'buyer',
      name: values.name,
      phone: values.phone,
      email: values.email,
      social_media: values.social_media,
      lead_source: values.lead_source,
    })
    pickerView.value = 'search'
  } catch (error) {
    buyerErrorMessage.value = (error as ApiError).message
  } finally {
    isSavingBuyer.value = false
  }
}

const isReserving = ref(false)
const reserveErrorMessage = ref('')

async function handleReserveConfirm(): Promise<void> {
  if (!selectedBuyer.value) {
    return
  }
  reserveErrorMessage.value = ''
  isReserving.value = true
  try {
    await listingStore.reserveListing(props.listing.id)
    emit('reserved')
  } catch (error) {
    reserveErrorMessage.value = (error as ApiError).message
  } finally {
    isReserving.value = false
  }
}
</script>

<template>
  <BaseModal :title="t('listingDetails.markReservedModalTitle')" @close="emit('close')">
    <div class="space-y-4">
      <!-- SelectedBuyerSummary -->
      <div v-if="selectedBuyer" class="rounded-md border border-border bg-muted/30 p-3">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingDetails.selectedBuyerLabel') }}</p>
        <p class="mt-0.5 text-sm font-medium text-foreground">{{ selectedBuyer.name }}</p>
        <p class="text-xs text-muted-foreground">{{ selectedBuyer.phone }}</p>
      </div>

      <template v-else>
        <!-- SearchView -->
        <div v-if="pickerView === 'search'">
          <label class="block text-sm font-medium text-foreground" for="reserve-buyer-search">
            {{ t('listingDetails.selectBuyerLabel') }} <RequiredMark />
          </label>
          <div class="relative mt-1.5">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              id="reserve-buyer-search"
              v-model="searchQuery"
              type="text"
              :placeholder="t('crm.clients.picker.searchPlaceholder')"
              class="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
          </div>

          <div v-if="filteredClients.length === 0" class="py-6 text-center text-sm text-muted-foreground">
            {{ t('crm.clients.picker.noResults') }}
          </div>

          <ul v-else class="mt-2 max-h-56 space-y-1 overflow-y-auto">
            <li v-for="client in filteredClients" :key="client.id">
              <button
                type="button"
                :disabled="isSavingBuyer"
                class="flex w-full items-center gap-3 rounded-md border border-border p-2 text-left transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                @click="handlePickExisting(client)"
              >
                <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                  <UserGroupIcon class="size-4" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium text-foreground">{{ client.name }}</span>
                  <span class="block text-xs text-muted-foreground">{{ client.phone }}</span>
                </span>
              </button>
            </li>
          </ul>

          <button
            type="button"
            class="mt-3 flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            @click="pickerView = 'create'"
          >
            <PlusIcon class="size-4" />
            {{ t('crm.clients.picker.addNewButton') }}
          </button>
        </div>

        <!-- CreateView -->
        <div v-else>
          <div class="mb-3 flex items-center justify-between">
            <p class="text-sm font-medium text-foreground">{{ t('crm.clients.picker.addNewButton') }}</p>
            <button
              type="button"
              class="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline"
              @click="pickerView = 'search'"
            >
              {{ t('crm.clients.picker.backToListButton') }}
            </button>
          </div>
          <ClientForm
            :submit-label="t('common.buttons.add')"
            :submitting-label="t('common.buttons.adding')"
            @submit="handleCreateNewSubmit"
          />
        </div>
      </template>

      <!-- ErrorAlert -->
      <div
        v-if="buyerErrorMessage || reserveErrorMessage"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ buyerErrorMessage || reserveErrorMessage }}</span>
      </div>
    </div>

    <template #footer>
      <button
        type="button"
        class="flex-1 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        @click="emit('close')"
      >
        {{ t('common.buttons.cancel') }}
      </button>
      <button
        type="button"
        :disabled="!selectedBuyer || isReserving"
        class="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        @click="handleReserveConfirm"
      >
        {{ isReserving ? t('listingDetails.reservingButton') : t('listingDetails.confirmReserve') }}
      </button>
    </template>
  </BaseModal>
</template>
