<script setup lang="ts">
import { ChevronDownIcon, ChevronUpIcon, ExclamationTriangleIcon, LinkIcon } from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { Employee, EmployeeStats } from '~/types/employees'

const props = defineProps<{ employee: Employee }>()

const emit = defineEmits<{ 'view-clients': [] }>()

const { t, n, d } = useI18n()

const positionStore = usePositionStore()
const clientStore = useClientStore()
const employeeStore = useEmployeeStore()

const hasSocialLinks = computed<boolean>(() => props.employee.social_links.some((link) => link.trim().length > 0))

const positionName = computed<string | undefined>(() =>
  props.employee.position_id === null
    ? undefined
    : positionStore.positions.find((position) => position.id === props.employee.position_id)?.name
)

const assignedClientCount = computed<number>(() =>
  clientStore.clients.filter((client) => client.employee_id === props.employee.id).length
)

// Owner/co-founder-only, and lazy: GET /employees/{id}/stats only fires the
// first time this section is actually expanded, not for every card on the
// roster page.
const { isCompanyAdmin } = useUserRole()

const isStatsExpanded = ref(false)
const isStatsLoading = ref(false)
const statsErrorMessage = ref('')

const stats = computed<EmployeeStats | undefined>(() => employeeStore.statsByEmployeeId[props.employee.id])

async function toggleStats(): Promise<void> {
  isStatsExpanded.value = !isStatsExpanded.value
  if (!isStatsExpanded.value || stats.value) {
    return
  }

  statsErrorMessage.value = ''
  isStatsLoading.value = true
  try {
    await employeeStore.fetchEmployeeStats(props.employee.id)
  } catch (error) {
    statsErrorMessage.value = (error as ApiError).message
  } finally {
    isStatsLoading.value = false
  }
}

const statusBadgeClasses: Record<string, string> = {
  completed: 'bg-success/10 text-success',
  in_progress: 'bg-amber-500/10 text-amber-600',
  no_plan: 'bg-muted text-muted-foreground',
}

const formattedStartedAt = (value: string): string => d(new Date(value), 'short')
</script>

<template>
  <div class="space-y-4">
    <span
      class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold"
      :class="employee.is_active ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'"
    >
      {{ employee.is_active ? t('crm.employees.activeStatus') : t('crm.employees.inactiveStatus') }}
    </span>

    <dl class="grid grid-cols-1 gap-4">
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.emailLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ employee.email }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.form.phoneLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ employee.phone || '—' }}</dd>
      </div>
      <div>
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.form.positionLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ positionName || t('crm.employees.form.positionNotAssigned') }}</dd>
      </div>
      <div class="flex items-center gap-3">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.assignedClientsCount', { count: assignedClientCount }) }}</dt>
        <dd v-if="assignedClientCount > 0">
          <button type="button" class="text-sm font-medium text-primary hover:underline" @click="emit('view-clients')">
            {{ t('crm.employees.viewClientsLink') }}
          </button>
        </dd>
      </div>
      <div v-if="hasSocialLinks">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.form.socialLinksLabel') }}</dt>
        <dd class="mt-0.5 space-y-1">
          <p
            v-for="link in employee.social_links.filter((link) => link.trim().length > 0)"
            :key="link"
            class="flex items-center gap-1.5 text-sm text-foreground"
          >
            <LinkIcon class="size-3.5 shrink-0 text-muted-foreground" />
            {{ link }}
          </p>
        </dd>
      </div>
    </dl>

    <!-- StatsSection -->
    <div v-if="isCompanyAdmin" class="border-t border-border pt-4">
      <button
        type="button"
        class="flex w-full items-center justify-between text-left text-sm font-medium text-foreground"
        @click="toggleStats"
      >
        {{ t('crm.employees.stats.sectionTitle') }}
        <ChevronUpIcon v-if="isStatsExpanded" class="size-4 shrink-0 text-muted-foreground" />
        <ChevronDownIcon v-else class="size-4 shrink-0 text-muted-foreground" />
      </button>

      <div v-if="isStatsExpanded" class="mt-3 space-y-3">
        <p v-if="isStatsLoading" class="text-sm text-muted-foreground">{{ t('crm.employees.stats.loading') }}</p>

        <div
          v-else-if="statsErrorMessage"
          class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ statsErrorMessage }}</span>
        </div>

        <dl v-else-if="stats" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.startedAtLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ formattedStartedAt(stats.started_at) }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.totalSoldLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ n(stats.total_sold_count, 'decimal') }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.averageCheckLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ stats.average_check === null ? '—' : n(stats.average_check, 'currency') }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.totalProfitLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ n(stats.total_profit_brought, 'currency') }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.currentMonthPlanLabel') }}</dt>
            <dd class="mt-0.5">
              <span
                v-if="stats.current_month_plan.target_count === null"
                class="text-sm text-muted-foreground"
              >
                {{ t('crm.employees.stats.noPlanAssigned') }}
              </span>
              <span v-else class="inline-flex items-center gap-1.5">
                <span class="text-sm text-foreground">
                  {{ stats.current_month_plan.actual_count }} / {{ stats.current_month_plan.target_count }}
                  <template v-if="stats.current_month_plan.percent !== null"> ({{ stats.current_month_plan.percent }}%)</template>
                </span>
                <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="statusBadgeClasses[stats.current_month_plan.status]">
                  {{ t(`crm.salesPlans.status.${stats.current_month_plan.status}`) }}
                </span>
              </span>
            </dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.plansCompletedLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ stats.plans_completed_count }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.plansMissedLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">{{ stats.plans_missed_count }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.stats.efficiencyRateLabel') }}</dt>
            <dd class="mt-0.5 text-sm text-foreground">
              {{ stats.efficiency_rate === null ? t('crm.employees.stats.noDataYet') : `${stats.efficiency_rate}%` }}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  </div>
</template>
