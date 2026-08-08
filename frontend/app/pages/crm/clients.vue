<script setup lang="ts">
import { Cog6ToothIcon, ListBulletIcon, PlusIcon, ViewColumnsIcon } from '@heroicons/vue/24/outline'
import type { Client } from '~/types/clients'
import type { Employee } from '~/types/employees'
import type { ClientType } from '~/utils/clientStages'
import type { EmployeeFilterToken } from '~/utils/clientEmployeeFilter'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t } = useI18n()

const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const listingStore = useListingStore()
const employeeStore = useEmployeeStore()

const activeTab = ref<ClientType>('seller')
const viewMode = ref<'kanban' | 'list'>('kanban')

// Shared between Kanban and List — switching view mode must not reset it.
const employeeFilterTokens = ref<EmployeeFilterToken[]>([])
const activeEmployeesForFilter = computed<Employee[]>(() => employeeStore.employees.filter((employee) => employee.is_active))

await Promise.all([
  clientStore.fetchClients(),
  clientStageStore.fetchStages(),
  listingStore.fetchListings(),
  employeeStore.fetchEmployees(),
])

const isAddModalOpen = ref(false)
const isBoardSettingsOpen = ref(false)
const selectedClientId = ref<number | null>(null)

// Derived live from the store (not a static snapshot) so that saving an
// edit in ClientDetailModal is reflected immediately in the read-only view,
// instead of showing stale pre-edit values. Shared here (rather than inside
// each view component) so both Kanban and List open the exact same modal
// instance/state instead of duplicating it.
const selectedClient = computed<Client | undefined>(() =>
  selectedClientId.value === null
    ? undefined
    : clientStore.clients.find((client) => client.id === selectedClientId.value)
)

function handleClientSelect(client: Client): void {
  selectedClientId.value = client.id
}

function handleClientCreated(): void {
  isAddModalOpen.value = false
}

function handleClientDeleted(): void {
  selectedClientId.value = null
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold text-foreground">{{ t('crm.clients.title') }}</h1>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="inline-flex gap-1 rounded-md bg-muted p-1">
        <button
          type="button"
          class="whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="activeTab === 'seller' ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = 'seller'"
        >
          {{ t('crm.clients.tabs.sellers') }}
        </button>
        <button
          type="button"
          class="whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="activeTab === 'buyer' ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = 'buyer'"
        >
          {{ t('crm.clients.tabs.buyers') }}
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <ClientEmployeeFilterDropdown v-model="employeeFilterTokens" :employees="activeEmployeesForFilter" />

        <!-- ViewModeToggle -->
        <div class="inline-flex gap-1 rounded-md bg-muted p-1" role="group" :aria-label="t('crm.clients.viewMode.label')">
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors"
            :class="viewMode === 'kanban' ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
            :title="t('crm.clients.viewMode.kanban')"
            :aria-label="t('crm.clients.viewMode.kanban')"
            @click="viewMode = 'kanban'"
          >
            <ViewColumnsIcon class="size-4" />
          </button>
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors"
            :class="viewMode === 'list' ? 'bg-surface text-foreground shadow-card' : 'text-muted-foreground hover:text-foreground'"
            :title="t('crm.clients.viewMode.list')"
            :aria-label="t('crm.clients.viewMode.list')"
            @click="viewMode = 'list'"
          >
            <ListBulletIcon class="size-4" />
          </button>
        </div>

        <button
          type="button"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isBoardSettingsOpen = true"
        >
          <Cog6ToothIcon class="size-4" />
          {{ t('crm.clients.boardSettings.openButton') }}
        </button>

        <button
          v-if="activeTab === 'buyer'"
          type="button"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
          @click="isAddModalOpen = true"
        >
          <PlusIcon class="size-4" />
          {{ t('crm.clients.addButton') }}
        </button>
      </div>
    </div>

    <ClientKanbanBoard
      v-if="viewMode === 'kanban'"
      :client-type="activeTab"
      :employee-filter-tokens="employeeFilterTokens"
      @select="handleClientSelect"
    />
    <ClientListView
      v-else
      :client-type="activeTab"
      :employee-filter-tokens="employeeFilterTokens"
      @select="handleClientSelect"
    />

    <ClientFormModal
      v-if="isAddModalOpen"
      :client-type="activeTab"
      @close="isAddModalOpen = false"
      @created="handleClientCreated"
    />

    <ClientDetailModal
      v-if="selectedClient"
      :client="selectedClient"
      @close="selectedClientId = null"
      @deleted="handleClientDeleted"
    />

    <BoardSettingsModal
      v-if="isBoardSettingsOpen"
      :client-type="activeTab"
      @close="isBoardSettingsOpen = false"
    />
  </div>
</template>
