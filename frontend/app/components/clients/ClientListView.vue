<script setup lang="ts">
import { ChevronDownIcon, ChevronUpIcon, MagnifyingGlassIcon, UsersIcon } from '@heroicons/vue/24/outline'
import type { Client, ClientStage } from '~/types/clients'
import type { Listing } from '~/types/listings'
import type { ClientType } from '~/utils/clientStages'
import { getClientStageColorClasses } from '~/utils/clientStageColors'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'
import { clientMatchesEmployeeFilter, type EmployeeFilterToken } from '~/utils/clientEmployeeFilter'

// Two mutually exclusive usages: the Clients board passes clientType and
// reads the shared clientStore.clients (filtered locally, per board-wide
// convention); the employee's "Переглянути клієнтів" modal instead passes a
// pre-fetched, employee-scoped clients array (both client types together) —
// in that mode the Employee column is replaced by a Type column since every
// row already shares the same employee. employeeFilterTokens only applies
// to the Clients board usage (the employee-scoped modal is pre-filtered).
const props = defineProps<{
  clientType?: ClientType
  clients?: Client[]
  employeeFilterTokens?: EmployeeFilterToken[]
}>()

const emit = defineEmits<{ select: [client: Client] }>()

const authStore = useAuthStore()

const showTypeColumn = computed<boolean>(() => props.clients !== undefined)

type SortColumn = 'name' | 'stage' | 'created_at'

const { t, d } = useI18n()

const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const listingStore = useListingStore()

const searchQuery = ref('')
const selectedStageId = ref<number | ''>('')
const sortColumn = ref<SortColumn>('created_at')
const sortDirection = ref<'asc' | 'desc'>('desc')

const stagesForType = computed<ClientStage[]>(() =>
  clientStageStore.stages
    .filter((stage) => props.clientType === undefined || stage.client_type === props.clientType)
    .sort((a, b) => a.order - b.order)
)

const stageById = computed<Map<number, ClientStage>>(() => new Map(clientStageStore.stages.map((stage) => [stage.id, stage])))
const listingById = computed<Map<number, Listing>>(() => new Map(listingStore.listings.map((listing) => [listing.id, listing])))

function stageForClient(client: Client): ClientStage | undefined {
  return stageById.value.get(client.stage_id)
}

function listingForClient(client: Client): Listing | undefined {
  return listingById.value.get(client.listing_id)
}

function employeeNameForClient(client: Client): string | undefined {
  return getEmployeeDisplayName(client.employee)
}

const filteredClients = computed<Client[]>(() => {
  let result = props.clients ?? clientStore.clients.filter((client) => client.client_type === props.clientType)

  if (props.employeeFilterTokens && props.employeeFilterTokens.length > 0) {
    result = result.filter((client) => clientMatchesEmployeeFilter(client, props.employeeFilterTokens!, authStore.user?.id))
  }

  if (selectedStageId.value !== '') {
    result = result.filter((client) => client.stage_id === selectedStageId.value)
  }

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    result = result.filter((client) =>
      client.name.toLowerCase().includes(query) || client.phone.toLowerCase().includes(query)
    )
  }

  return result
})

const sortedClients = computed<Client[]>(() => {
  const items = [...filteredClients.value]

  items.sort((a, b) => {
    let comparison = 0
    if (sortColumn.value === 'name') {
      comparison = a.name.localeCompare(b.name)
    } else if (sortColumn.value === 'created_at') {
      comparison = a.created_at.localeCompare(b.created_at)
    } else if (sortColumn.value === 'stage') {
      comparison = (stageForClient(a)?.order ?? 0) - (stageForClient(b)?.order ?? 0)
    }
    return sortDirection.value === 'asc' ? comparison : -comparison
  })

  return items
})

function toggleSort(column: SortColumn): void {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'asc'
  }
}

const formattedDate = (value: string): string => d(new Date(value), 'short')
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <div class="relative flex-1 sm:max-w-xs">
        <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('crm.clients.list.searchPlaceholder')"
          class="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <select
        v-model="selectedStageId"
        class="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">{{ t('crm.clients.list.allStages') }}</option>
        <option v-for="stage in stagesForType" :key="stage.id" :value="stage.id">{{ stage.name }}</option>
      </select>
    </div>

    <!-- ListEmptyState -->
    <div
      v-if="sortedClients.length === 0"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <UsersIcon class="size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ t('crm.clients.list.empty') }}</p>
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="cursor-pointer select-none whitespace-nowrap px-4 py-3 font-medium" @click="toggleSort('name')">
              <span class="inline-flex items-center gap-1">
                {{ t('crm.clients.list.columns.name') }}
                <ChevronUpIcon v-if="sortColumn === 'name' && sortDirection === 'asc'" class="size-3.5" />
                <ChevronDownIcon v-if="sortColumn === 'name' && sortDirection === 'desc'" class="size-3.5" />
              </span>
            </th>
            <th class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.phone') }}</th>
            <th class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.email') }}</th>
            <th class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.socialMedia') }}</th>
            <th class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.listing') }}</th>
            <th class="cursor-pointer select-none whitespace-nowrap px-4 py-3 font-medium" @click="toggleSort('stage')">
              <span class="inline-flex items-center gap-1">
                {{ t('crm.clients.list.columns.stage') }}
                <ChevronUpIcon v-if="sortColumn === 'stage' && sortDirection === 'asc'" class="size-3.5" />
                <ChevronDownIcon v-if="sortColumn === 'stage' && sortDirection === 'desc'" class="size-3.5" />
              </span>
            </th>
            <th v-if="showTypeColumn" class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.type') }}</th>
            <th v-else class="whitespace-nowrap px-4 py-3 font-medium">{{ t('crm.clients.list.columns.employee') }}</th>
            <th class="cursor-pointer select-none whitespace-nowrap px-4 py-3 font-medium" @click="toggleSort('created_at')">
              <span class="inline-flex items-center gap-1">
                {{ t('crm.clients.list.columns.createdAt') }}
                <ChevronUpIcon v-if="sortColumn === 'created_at' && sortDirection === 'asc'" class="size-3.5" />
                <ChevronDownIcon v-if="sortColumn === 'created_at' && sortDirection === 'desc'" class="size-3.5" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr
            v-for="client in sortedClients"
            :key="client.id"
            class="cursor-pointer transition-colors hover:bg-muted"
            @click="emit('select', client)"
          >
            <td class="px-4 py-3 font-medium text-foreground">{{ client.name }}</td>
            <td class="px-4 py-3 text-foreground">{{ client.phone }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ client.email || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ client.social_media || '—' }}</td>
            <td class="px-4 py-3">
              <NuxtLink
                v-if="listingForClient(client)"
                :to="`/crm/inventory/${client.listing_id}`"
                class="font-medium text-primary hover:underline"
                @click.stop
              >
                {{ listingForClient(client)!.brand }} {{ listingForClient(client)!.model }}, {{ listingForClient(client)!.year }}
              </NuxtLink>
              <span v-else class="text-muted-foreground">—</span>
            </td>
            <td class="px-4 py-3">
              <span
                v-if="stageForClient(client)"
                class="rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="getClientStageColorClasses(stageForClient(client)!.order)"
              >
                {{ stageForClient(client)!.name }}
              </span>
              <span v-else class="text-muted-foreground">—</span>
            </td>
            <td v-if="showTypeColumn" class="px-4 py-3 text-muted-foreground">{{ t(`crm.clients.typeLabels.${client.client_type}`) }}</td>
            <td v-else class="px-4 py-3 text-muted-foreground">{{ employeeNameForClient(client) || '—' }}</td>
            <td class="whitespace-nowrap px-4 py-3 text-muted-foreground">{{ formattedDate(client.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
