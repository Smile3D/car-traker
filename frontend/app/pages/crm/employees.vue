<script setup lang="ts">
import { Cog6ToothIcon, UserGroupIcon, UserPlusIcon } from '@heroicons/vue/24/outline'
import type { Client } from '~/types/clients'
import type { Employee } from '~/types/employees'
import type { EmployeeInvite } from '~/types/employeeInvites'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, d } = useI18n()

const authStore = useAuthStore()

// The roster itself is visible to any company member; inviting new
// employees, managing positions, and editing/deactivating a colleague stay
// owner/co-founder-only (gated below, both in the UI and on the backend).
const { isOwner, isCompanyAdmin } = useUserRole()

const employeeStore = useEmployeeStore()
const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const listingStore = useListingStore()
const positionStore = usePositionStore()
const employeeInviteStore = useEmployeeInviteStore()

const fetchTasks = [
  employeeStore.fetchEmployees(),
  clientStore.fetchClients(),
  clientStageStore.fetchStages(),
  listingStore.fetchListings(),
  positionStore.fetchPositions(),
]
// GET /employees/invites is owner/co-founder-only — fetching it for a plain
// employee would just be a wasted 403.
if (isCompanyAdmin.value) {
  fetchTasks.push(employeeInviteStore.fetchInvites())
}
await Promise.all(fetchTasks)

const selectedEmployeeId = ref<number | null>(null)
const isManagePositionsOpen = ref(false)
const isInviteModalOpen = ref(false)

// Two-modal stack (rather than one boolean) so "Переглянути клієнтів" can
// swap the employee modal out for the clients-list modal, and closing that
// one goes back to the employee modal instead of closing everything.
const showEmployeeModal = ref(false)
const showEmployeeClientsModal = ref(false)
const selectedClientId = ref<number | null>(null)

// Derived live from the store (not a static snapshot) so deactivating or
// reactivating in the detail modal is reflected immediately.
const selectedEmployee = computed<Employee | undefined>(() =>
  selectedEmployeeId.value === null
    ? undefined
    : employeeStore.employees.find((employee) => employee.id === selectedEmployeeId.value)
)

const selectedClient = computed<Client | undefined>(() =>
  selectedClientId.value === null
    ? undefined
    : clientStore.clients.find((client) => client.id === selectedClientId.value)
)

// A non-owner viewer (employee or co-founder) sees the rest of the team, not
// their own card — this is display-only for the roster page.
// employeeStore.employees itself stays untouched, so the
// "Відповідальний співробітник" assignment select elsewhere (which reads
// that same store) still lets an employee assign themselves; only this
// page's own list filters self out. This must stay isOwner, not
// isCompanyAdmin: the roster now includes co-founders too (see backend
// list_employees), so a co-founder viewing this page WOULD find their own
// id in employeeStore.employees — only isOwner correctly triggers
// self-exclusion for them. Owner viewers are unaffected since the owner's
// own record is never in this roster to begin with.
const visibleEmployees = computed<Employee[]>(() =>
  isOwner.value
    ? employeeStore.employees
    : employeeStore.employees.filter((employee) => employee.id !== authStore.user?.id)
)

// Active employees first, inactive ones at the end.
const sortedEmployees = computed<Employee[]>(() =>
  [...visibleEmployees.value].sort((a, b) => Number(b.is_active) - Number(a.is_active))
)

function openEmployeeDetail(employee: Employee): void {
  selectedEmployeeId.value = employee.id
  showEmployeeModal.value = true
}

function closeEmployeeModal(): void {
  showEmployeeModal.value = false
  selectedEmployeeId.value = null
}

function openEmployeeClients(): void {
  showEmployeeModal.value = false
  showEmployeeClientsModal.value = true
}

function closeEmployeeClientsModal(): void {
  // Back to the employee modal — same employee, nothing to refetch.
  showEmployeeClientsModal.value = false
  showEmployeeModal.value = true
}

function handleClientSelect(client: Client): void {
  // Leaving the employee-detail context entirely for the client's own card,
  // so the whole modal stack closes rather than just the top of it.
  showEmployeeClientsModal.value = false
  selectedEmployeeId.value = null
  selectedClientId.value = client.id
}

function handleClientDeleted(): void {
  selectedClientId.value = null
}

function positionNameById(positionId: number | null): string | undefined {
  return positionId === null ? undefined : positionStore.positions.find((position) => position.id === positionId)?.name
}

const inviteStatusBadgeClasses: Record<EmployeeInvite['status'], string> = {
  active: 'bg-success/10 text-success',
  used: 'bg-primary/10 text-primary',
  revoked: 'bg-muted text-muted-foreground',
  expired: 'bg-destructive/10 text-destructive',
}

const formattedDate = (value: string): string => d(new Date(value), 'short')

const invitePendingRevoke = ref<EmployeeInvite | null>(null)

async function handleConfirmRevoke(reason: string | undefined): Promise<void> {
  if (!invitePendingRevoke.value) {
    return
  }

  await employeeInviteStore.revokeInvite(invitePendingRevoke.value.id, { cancellation_reason: reason })
  invitePendingRevoke.value = null
}

// Clicking an invite row: active → reopen the same link+copy modal used
// right after generation; anything else → the link is already dead, show a
// small status-details view instead (used-at / cancellation reason / etc).
const reopenInviteToken = ref<string | null>(null)
const inviteForStatusInfo = ref<EmployeeInvite | null>(null)

function handleInviteRowClick(invite: EmployeeInvite): void {
  if (invite.status === 'active' && invite.token) {
    reopenInviteToken.value = invite.token
  } else {
    inviteForStatusInfo.value = invite
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.employees.title') }}</h1>

      <div v-if="isCompanyAdmin" class="flex flex-wrap gap-2">
        <button
          type="button"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isManagePositionsOpen = true"
        >
          <Cog6ToothIcon class="size-4" />
          {{ t('crm.employees.positions.manageButton') }}
        </button>
        <button
          type="button"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
          @click="isInviteModalOpen = true"
        >
          <UserPlusIcon class="size-4" />
          {{ t('crm.employees.invites.inviteButton') }}
        </button>
      </div>
    </div>

    <!-- EmptyState -->
    <div
      v-if="sortedEmployees.length === 0"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <UserGroupIcon class="size-6" />
      </span>
      <div>
        <p class="font-medium text-foreground">{{ t('crm.employees.emptyTitle') }}</p>
        <p class="mt-1 text-sm text-muted-foreground">{{ t('crm.employees.emptySubtitle') }}</p>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <EmployeeCard
        v-for="employee in sortedEmployees"
        :key="employee.id"
        :employee="employee"
        @click="openEmployeeDetail(employee)"
      />
    </div>

    <!-- InvitesSection -->
    <section v-if="isCompanyAdmin" class="space-y-3">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.invites.sectionTitle') }}</h2>

      <div
        v-if="employeeInviteStore.invites.length === 0"
        class="rounded-lg border border-dashed border-border-strong bg-surface px-6 py-8 text-center text-sm text-muted-foreground"
      >
        {{ t('crm.employees.invites.empty') }}
      </div>

      <div v-else class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th class="px-4 py-3 font-medium">{{ t('crm.employees.invites.columns.email') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.employees.invites.columns.position') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.employees.invites.columns.createdAt') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.employees.invites.columns.status') }}</th>
              <th class="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="invite in employeeInviteStore.invites"
              :key="invite.id"
              class="cursor-pointer transition-colors hover:bg-muted"
              @click="handleInviteRowClick(invite)"
            >
              <td class="px-4 py-3 text-foreground">{{ invite.email || t('crm.employees.invites.noEmailRestriction') }}</td>
              <td class="px-4 py-3 text-muted-foreground">{{ positionNameById(invite.position_id) || '—' }}</td>
              <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(invite.created_at) }}</td>
              <td class="px-4 py-3">
                <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="inviteStatusBadgeClasses[invite.status]">
                  {{ t(`crm.employees.invites.status.${invite.status}`) }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="invite.status === 'active'"
                  type="button"
                  class="rounded-md border border-destructive/30 px-2.5 py-1 text-xs font-medium text-destructive transition-colors hover:bg-destructive/10"
                  @click.stop="invitePendingRevoke = invite"
                >
                  {{ t('crm.employees.invites.cancelButton') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <EmployeeDetailModal
      v-if="showEmployeeModal && selectedEmployee"
      :employee="selectedEmployee"
      @close="closeEmployeeModal"
      @view-clients="openEmployeeClients"
    />

    <EmployeeClientsModal
      v-if="showEmployeeClientsModal && selectedEmployee"
      :employee="selectedEmployee"
      @close="closeEmployeeClientsModal"
      @select-client="handleClientSelect"
    />

    <ClientDetailModal
      v-if="selectedClient"
      :client="selectedClient"
      @close="selectedClientId = null"
      @deleted="handleClientDeleted"
    />

    <PositionsManageModal
      v-if="isManagePositionsOpen"
      @close="isManagePositionsOpen = false"
    />

    <EmployeeInviteModal
      v-if="isInviteModalOpen"
      @close="isInviteModalOpen = false"
    />

    <EmployeeInviteModal
      v-if="reopenInviteToken"
      :existing-token="reopenInviteToken"
      @close="reopenInviteToken = null"
    />

    <InviteStatusInfoModal
      v-if="inviteForStatusInfo"
      :invite="inviteForStatusInfo"
      @close="inviteForStatusInfo = null"
    />

    <InviteCancelConfirmModal
      v-if="invitePendingRevoke"
      @confirm="handleConfirmRevoke"
      @cancel="invitePendingRevoke = null"
    />
  </div>
</template>
