<script setup lang="ts">
import { TrashIcon, UserGroupIcon } from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { Client, ClientEmployeeSummary } from '~/types/clients'
import type { Employee } from '~/types/employees'
import type { ListingStatus } from '~/types/listings'
import { getLeadSourceLabelKey } from '~/utils/clientOptions'
import { getClientStageColorClasses } from '~/utils/clientStageColors'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'
import { getListingStatusBadgeClasses } from '~/utils/listingStatus'

const props = withDefaults(defineProps<{
  listingId: number
  listingStatus: ListingStatus
  isEditMode?: boolean
  isArchived?: boolean
  isForeignListing?: boolean
}>(), {
  isEditMode: false,
  isArchived: false,
  isForeignListing: false,
})

const emit = defineEmits<{ 'employee-change': [buyerId: number, employeeId: number | null] }>()

const { t } = useI18n()

const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const employeeStore = useEmployeeStore()

// A listing can have at most one buyer (same one-per-listing cap as the
// seller, enforced backend-side by a partial unique index + a 409 on
// create). Still modeled as an array and rendered via v-for rather than a
// single optional object, so the display keeps working with no changes if
// that cap is ever lifted — derived from the already-fetched full client
// list, same as ListingSellerSection, no dedicated
// GET /clients?listing_id=... request needed for this page even though the
// backend now supports one.
const buyerClients = computed<Client[]>(() =>
  clientStore.clients
    .filter((client) => client.listing_id === props.listingId && client.client_type === 'buyer')
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
)

function stageFor(buyer: Client) {
  return clientStageStore.stages.find((stage) => stage.id === buyer.stage_id)
}

// Mirrors ListingSellerSection's assignableEmployees: the currently assigned
// employee stays selectable even if since deactivated, so an existing
// assignment is never silently hidden — every other option is restricted to
// active employees.
function assignableEmployeesFor(buyer: Client): Employee[] {
  const activeEmployees = employeeStore.employees.filter((employee) => employee.is_active)
  const currentEmployeeId = buyer.employee_id
  if (currentEmployeeId != null && !activeEmployees.some((employee) => employee.id === currentEmployeeId)) {
    const currentEmployee = employeeStore.employees.find((employee) => employee.id === currentEmployeeId)
    if (currentEmployee) {
      return [...activeEmployees, currentEmployee]
    }
  }
  return activeEmployees
}

// GET /employees is owner-only, so employeeStore.employees is empty for an
// employee viewer — without this, the select would show blank instead of
// their own name. ClientOut already embeds this summary on the buyer Client
// itself, so it's available regardless of role.
function currentAssignedEmployeeFallbackFor(buyer: Client): ClientEmployeeSummary | null {
  const currentEmployeeId = buyer.employee_id
  if (currentEmployeeId == null || assignableEmployeesFor(buyer).some((employee) => employee.id === currentEmployeeId)) {
    return null
  }
  return buyer.employee ?? null
}

// One local edit value per buyer, keyed by client id — same read-only/edit
// toggle pattern as the seller section, just fanned out over N buyers.
const buyerEmployeeIdById = reactive<Record<number, number | ''>>({})

function syncBuyerEmployeeIds(): void {
  for (const buyer of buyerClients.value) {
    buyerEmployeeIdById[buyer.id] = buyer.employee_id ?? ''
  }
}

watch(buyerClients, syncBuyerEmployeeIds, { immediate: true })

// Same reasoning as ListingSellerSection: this component stays mounted
// across the page's view/edit toggle, so leaving edit mode — Cancel or a
// successful Save — needs to explicitly re-sync back to the persisted value.
watch(() => props.isEditMode, (editing) => {
  if (!editing) {
    syncBuyerEmployeeIds()
  }
})

function handleEmployeeSelectChange(buyerId: number): void {
  const value = buyerEmployeeIdById[buyerId]
  emit('employee-change', buyerId, value === '' || value === undefined ? null : Number(value))
}

const buyerPendingDeleteId = ref<number | null>(null)
const deleteErrorMessage = ref<string | null>(null)

function handleDeleteClick(buyerId: number): void {
  deleteErrorMessage.value = null
  buyerPendingDeleteId.value = buyerId
}

function handleDeleteCancel(): void {
  buyerPendingDeleteId.value = null
}

async function handleDeleteConfirm(reason: string | undefined): Promise<void> {
  if (buyerPendingDeleteId.value === null) {
    return
  }
  try {
    await clientStore.deleteClient(buyerPendingDeleteId.value, reason)
    buyerPendingDeleteId.value = null
  } catch (error) {
    deleteErrorMessage.value = (error as ApiError).message
  }
}
</script>

<template>
  <section class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card">
    <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingDetails.buyersSection') }}</h2>

    <div v-if="buyerClients.length === 0" class="flex items-center gap-2 text-sm text-muted-foreground">
      <UserGroupIcon class="size-4 shrink-0" />
      {{ t('listingDetails.noBuyers') }}
    </div>

    <div v-else class="divide-y divide-border">
      <div v-for="buyer in buyerClients" :key="buyer.id" class="py-3 first:pt-0 last:pb-0">
        <div class="flex flex-wrap items-center justify-end gap-3">
          <NuxtLink v-if="!isArchived" to="/crm/clients" class="text-xs font-medium text-primary hover:underline">
            {{ t('listingDetails.viewOnClientsBoard') }}
          </NuxtLink>
          <button
            v-if="!isArchived && !isForeignListing"
            type="button"
            class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            :aria-label="t('listingDetails.deleteBuyerButtonLabel')"
            :title="t('listingDetails.deleteBuyerButtonLabel')"
            @click="handleDeleteClick(buyer.id)"
          >
            <TrashIcon class="size-4" />
          </button>
        </div>

        <dl class="mt-1 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.nameLabel') }}</dt>
            <dd class="mt-0.5 flex items-center gap-2 text-sm text-foreground">
              {{ buyer.name }}
              <span
                v-if="listingStatus === 'reserved'"
                class="rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="getListingStatusBadgeClasses('reserved')"
              >
                {{ t('listingDetails.reservedBadge') }}
              </span>
            </dd>
          </div>

          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.phoneLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ buyer.phone }}</dd>
          </div>

          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.list.columns.stage') }}</dt>
            <dd class="mt-0.5">
              <span
                v-if="stageFor(buyer)"
                class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold"
                :class="getClientStageColorClasses(stageFor(buyer)!.order)"
              >
                {{ stageFor(buyer)!.name }}
              </span>
              <span v-else class="text-sm text-foreground">—</span>
            </dd>
          </div>

          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.leadSourceLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ buyer.lead_source ? t(getLeadSourceLabelKey(buyer.lead_source)) : t('crm.clients.form.leadSourceNotSpecified') }}</dd>
          </div>

          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.employeeLabel') }}</dt>
            <dd class="mt-0.5">
              <select
                v-model="buyerEmployeeIdById[buyer.id]"
                :disabled="!isEditMode"
                class="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
                @change="handleEmployeeSelectChange(buyer.id)"
              >
                <option value="">{{ t('crm.clients.form.employeeNotAssigned') }}</option>
                <option v-if="currentAssignedEmployeeFallbackFor(buyer)" :value="currentAssignedEmployeeFallbackFor(buyer)!.id">
                  {{ getEmployeeDisplayName(currentAssignedEmployeeFallbackFor(buyer), currentAssignedEmployeeFallbackFor(buyer)!.email) }}
                </option>
                <option v-for="employee in assignableEmployeesFor(buyer)" :key="employee.id" :value="employee.id">
                  {{ getEmployeeDisplayName(employee, employee.email) }}
                </option>
              </select>
            </dd>
          </div>
        </dl>
      </div>
    </div>

    <div
      v-if="deleteErrorMessage"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <span>{{ deleteErrorMessage }}</span>
    </div>

    <BuyerDeleteConfirmModal
      v-if="buyerPendingDeleteId !== null"
      @confirm="handleDeleteConfirm"
      @cancel="handleDeleteCancel"
    />
  </section>
</template>
