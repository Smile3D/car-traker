<script setup lang="ts">
import { EnvelopeIcon } from '@heroicons/vue/24/outline'
import type { Employee } from '~/types/employees'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ employee: Employee }>()

const { t } = useI18n()

const clientStore = useClientStore()
const positionStore = usePositionStore()

const assignedClientCount = computed<number>(() =>
  clientStore.clients.filter((client) => client.employee_id === props.employee.id).length
)

const hasFullName = computed<boolean>(() => Boolean(props.employee.first_name || props.employee.last_name))
const displayName = computed<string>(() => getEmployeeDisplayName(props.employee, props.employee.email) ?? props.employee.email)

const positionName = computed<string | undefined>(() =>
  props.employee.position_id === null
    ? undefined
    : positionStore.positions.find((position) => position.id === props.employee.position_id)?.name
)
</script>

<template>
  <div
    class="cursor-pointer space-y-2 rounded-md border border-border bg-surface p-4 shadow-card transition-colors hover:border-primary/40"
    :class="{ 'opacity-60': !employee.is_active }"
  >
    <div class="flex items-start justify-between gap-2">
      <div>
        <p class="text-sm font-semibold text-foreground">{{ displayName }}</p>
        <p v-if="hasFullName" class="flex items-center gap-1.5 text-xs text-muted-foreground">
          <EnvelopeIcon class="size-3.5 shrink-0" />
          {{ employee.email }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-1.5">
        <span
          v-if="employee.role === 'co_founder'"
          class="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
        >
          {{ t('crm.employees.coFounderBadge') }}
        </span>
        <span
          v-if="!employee.is_active"
          class="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
        >
          {{ t('crm.employees.inactiveStatus') }}
        </span>
      </div>
    </div>

    <p v-if="positionName" class="text-xs text-muted-foreground">{{ positionName }}</p>

    <p class="text-xs text-muted-foreground">
      {{ t('crm.employees.assignedClientsCount', { count: assignedClientCount }) }}
    </p>
  </div>
</template>
