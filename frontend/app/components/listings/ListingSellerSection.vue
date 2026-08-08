<script setup lang="ts">
import { UserGroupIcon } from '@heroicons/vue/24/outline'
import type { Employee } from '~/types/employees'
import { getLeadSourceLabelKey } from '~/utils/clientOptions'
import { getClientStageColorClasses } from '~/utils/clientStageColors'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = withDefaults(defineProps<{
  listingId: number
  isEditMode?: boolean
  isArchived?: boolean
}>(), {
  isEditMode: false,
  isArchived: false,
})

const emit = defineEmits<{ 'employee-change': [employeeId: number | null] }>()

const { t } = useI18n()

const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const employeeStore = useEmployeeStore()

// Derived from the already-fetched full client list (no dedicated
// GET /clients?listing_id=... endpoint needed) — a listing can have at most
// one seller-type client, enforced at the DB level.
const sellerClient = computed(() =>
  clientStore.clients.find((client) => client.listing_id === props.listingId && client.client_type === 'seller')
)

const sellerStage = computed(() =>
  sellerClient.value
    ? clientStageStore.stages.find((stage) => stage.id === sellerClient.value!.stage_id)
    : undefined
)

// The currently assigned employee stays selectable even if they've since
// been deactivated, so an existing assignment is never silently hidden —
// every other option is restricted to active employees.
const assignableEmployees = computed<Employee[]>(() => {
  const activeEmployees = employeeStore.employees.filter((employee) => employee.is_active)
  const currentEmployeeId = sellerClient.value?.employee_id
  if (currentEmployeeId != null && !activeEmployees.some((employee) => employee.id === currentEmployeeId)) {
    const currentEmployee = employeeStore.employees.find((employee) => employee.id === currentEmployeeId)
    if (currentEmployee) {
      return [...activeEmployees, currentEmployee]
    }
  }
  return activeEmployees
})

// GET /employees is owner-only, so employeeStore.employees is empty for an
// employee viewer — without this, the select would show blank instead of
// their own name. ClientOut already embeds this summary on the seller Client
// itself, so it's available regardless of role.
const currentAssignedEmployeeFallback = computed(() => {
  const currentEmployeeId = sellerClient.value?.employee_id
  if (currentEmployeeId == null || assignableEmployees.value.some((employee) => employee.id === currentEmployeeId)) {
    return null
  }
  return sellerClient.value?.employee ?? null
})

// Only the responsible-employee select is ever interactive here (and only
// while the listing itself is in edit mode) — name/phone/email/stage stay
// read-only on this page regardless of mode; editing the seller's own
// details happens on the Clients board instead.
const sellerEmployeeId = ref<number | ''>('')
watch(sellerClient, (client) => {
  sellerEmployeeId.value = client?.employee_id ?? ''
}, { immediate: true })

// This component stays mounted across the page's view/edit toggle (it's not
// swapped via v-if like ListingDetailsReadOnly/ListingForm), so leaving edit
// mode — whether via Cancel or a successful Save — needs to explicitly
// re-sync the select back to the persisted value instead of relying on a
// remount to reset it.
watch(() => props.isEditMode, (editing) => {
  if (!editing) {
    sellerEmployeeId.value = sellerClient.value?.employee_id ?? ''
  }
})

function handleEmployeeSelectChange(): void {
  emit('employee-change', sellerEmployeeId.value === '' ? null : Number(sellerEmployeeId.value))
}
</script>

<template>
  <section class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingDetails.sellerSection') }}</h2>
      <NuxtLink
        v-if="sellerClient && !isArchived"
        to="/crm/clients"
        class="text-xs font-medium text-primary hover:underline"
      >
        {{ t('listingDetails.viewOnClientsBoard') }}
      </NuxtLink>
    </div>

    <div v-if="!sellerClient" class="flex items-center gap-2 text-sm text-muted-foreground">
      <UserGroupIcon class="size-4 shrink-0" />
      {{ t('listingDetails.noSeller') }}
    </div>

    <dl v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.nameLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ sellerClient.name }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.phoneLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ sellerClient.phone }}</dd>
      </div>
      <div v-if="sellerClient.email">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.emailLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ sellerClient.email }}</dd>
      </div>
      <div v-if="sellerClient.social_media">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.socialMediaLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ sellerClient.social_media }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.leadSourceLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ sellerClient.lead_source ? t(getLeadSourceLabelKey(sellerClient.lead_source)) : t('crm.clients.form.leadSourceNotSpecified') }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.list.columns.stage') }}</dt>
        <dd class="mt-0.5">
          <span
            v-if="sellerStage"
            class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold"
            :class="getClientStageColorClasses(sellerStage.order)"
          >
            {{ sellerStage.name }}
          </span>
          <span v-else class="text-sm text-foreground">—</span>
        </dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.clients.form.employeeLabel') }}</dt>
        <dd class="mt-0.5">
          <select
            v-model="sellerEmployeeId"
            :disabled="!isEditMode"
            class="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
            @change="handleEmployeeSelectChange"
          >
            <option value="">{{ t('crm.clients.form.employeeNotAssigned') }}</option>
            <option v-if="currentAssignedEmployeeFallback" :value="currentAssignedEmployeeFallback.id">
              {{ getEmployeeDisplayName(currentAssignedEmployeeFallback, currentAssignedEmployeeFallback.email) }}
            </option>
            <option v-for="employee in assignableEmployees" :key="employee.id" :value="employee.id">
              {{ getEmployeeDisplayName(employee, employee.email) }}
            </option>
          </select>
        </dd>
      </div>
    </dl>
  </section>
</template>
