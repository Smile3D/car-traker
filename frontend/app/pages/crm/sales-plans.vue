<script setup lang="ts">
import { ExclamationTriangleIcon, FlagIcon } from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { SalesPlanProgress, SalesPlanStatus } from '~/types/salesPlans'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, n } = useI18n()

const salesPlanStore = useSalesPlanStore()

const { isCompanyAdmin } = useUserRole()

function currentMonthValue(): string {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
}

const selectedMonth = ref<string>(currentMonthValue())

async function loadPlans(): Promise<void> {
  await salesPlanStore.fetchSalesPlans(selectedMonth.value)
}

await loadPlans()

watch(selectedMonth, loadPlans)

const employeeRows = computed<SalesPlanProgress[]>(() => salesPlanStore.plans.filter((row) => !row.is_company_total))
const companyTotalRow = computed<SalesPlanProgress | undefined>(() => salesPlanStore.plans.find((row) => row.is_company_total))

function employeeName(row: SalesPlanProgress): string {
  return getEmployeeDisplayName(
    { first_name: row.employee_first_name, last_name: row.employee_last_name },
    row.employee_email
  ) ?? ''
}

const statusBadgeClasses: Record<SalesPlanStatus, string> = {
  completed: 'bg-success/10 text-success',
  in_progress: 'bg-amber-500/10 text-amber-600',
  no_plan: 'bg-muted text-muted-foreground',
}

const progressBarClasses: Record<SalesPlanStatus, string> = {
  completed: 'bg-success',
  in_progress: 'bg-primary',
  no_plan: 'bg-border-strong',
}

function progressBarWidth(row: SalesPlanProgress): string {
  if (!row.target_count) {
    return row.actual_count > 0 ? '100%' : '0%'
  }
  return `${Math.min(100, Math.round((row.actual_count / row.target_count) * 100))}%`
}

// Decoupled from the store rows on purpose (same reasoning as
// PositionsManageModal's editedNames) — binding the input directly to
// row.target_count would need a round-trip before the field reflects
// anything typed, and would briefly show a stale value while saving.
// Typed as string | number (not just string) because v-model on this
// type="number" input can hand back either depending on browser/how the
// value was set — always normalize with String(...) before treating it as
// text (see handleTargetBlur), never call string methods on it directly.
const editedTargets = reactive<Record<number, string | number>>({})

watchEffect(() => {
  for (const row of employeeRows.value) {
    if (row.employee_id !== null && !(row.employee_id in editedTargets)) {
      editedTargets[row.employee_id] = row.target_count === null ? '' : String(row.target_count)
    }
  }
})

const targetErrorByEmployeeId = reactive<Record<number, string>>({})

function currentSavedValue(row: SalesPlanProgress): string {
  return row.target_count === null ? '' : String(row.target_count)
}

async function handleTargetBlur(row: SalesPlanProgress): Promise<void> {
  if (row.employee_id === null) {
    return
  }

  const employeeId = row.employee_id
  delete targetErrorByEmployeeId[employeeId]

  const rawEditedValue = editedTargets[employeeId]
  const normalizedValue = rawEditedValue === null || rawEditedValue === undefined
    ? ''
    : String(rawEditedValue).trim()

  if (normalizedValue === currentSavedValue(row)) {
    return
  }

  const parsedValue = Number(normalizedValue)
  if (!normalizedValue || !Number.isInteger(parsedValue) || parsedValue <= 0) {
    targetErrorByEmployeeId[employeeId] = t('crm.salesPlans.invalidTargetError')
    editedTargets[employeeId] = currentSavedValue(row)
    return
  }

  try {
    await salesPlanStore.upsertSalesPlan({ employee_id: employeeId, month: selectedMonth.value, target_count: parsedValue })
    await loadPlans()
  } catch (error) {
    targetErrorByEmployeeId[employeeId] = (error as ApiError).message
    editedTargets[employeeId] = currentSavedValue(row)
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-xl font-semibold text-foreground">{{ t('crm.salesPlans.title') }}</h1>

      <div>
        <label class="sr-only" for="sales-plan-month">{{ t('crm.salesPlans.monthLabel') }}</label>
        <input
          id="sales-plan-month"
          v-model="selectedMonth"
          type="month"
          class="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>
    </div>

    <!-- OwnerView -->
    <div v-if="isCompanyAdmin">
      <div
        v-if="employeeRows.length === 0"
        class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
      >
        <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <FlagIcon class="size-6" />
        </span>
        <div>
          <p class="font-medium text-foreground">{{ t('crm.salesPlans.emptyTitle') }}</p>
          <p class="mt-1 text-sm text-muted-foreground">{{ t('crm.salesPlans.emptySubtitle') }}</p>
        </div>
      </div>

      <div v-else class="overflow-x-auto rounded-lg border border-border bg-surface shadow-card">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th class="px-4 py-3 font-medium">{{ t('crm.salesPlans.columns.employee') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.salesPlans.columns.target') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.salesPlans.columns.actual') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.salesPlans.columns.progress') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('crm.salesPlans.columns.status') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="row in employeeRows" :key="row.employee_id!">
              <td class="px-4 py-3 font-medium text-foreground">{{ employeeName(row) }}</td>
              <td class="px-4 py-3">
                <input
                  v-model="editedTargets[row.employee_id!]"
                  type="number"
                  min="1"
                  step="1"
                  :placeholder="t('crm.salesPlans.targetPlaceholder')"
                  class="w-24 rounded-md border border-border bg-surface px-2 py-1 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  @blur="handleTargetBlur(row)"
                  @keydown.enter="($event.target as HTMLInputElement).blur()"
                >
                <p v-if="targetErrorByEmployeeId[row.employee_id!]" class="mt-1 text-xs text-destructive">
                  {{ targetErrorByEmployeeId[row.employee_id!] }}
                </p>
              </td>
              <td class="px-4 py-3 tabular-nums text-foreground">{{ n(row.actual_count, 'decimal') }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-24 overflow-hidden rounded-full bg-muted">
                    <div class="h-full rounded-full transition-all" :class="progressBarClasses[row.status]" :style="{ width: progressBarWidth(row) }" />
                  </div>
                  <span class="whitespace-nowrap text-xs text-muted-foreground">
                    {{ row.target_count === null ? row.actual_count : `${row.actual_count} / ${row.target_count}` }}
                    <template v-if="row.percent !== null"> ({{ row.percent }}%)</template>
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="statusBadgeClasses[row.status]">
                  {{ t(`crm.salesPlans.status.${row.status}`) }}
                </span>
              </td>
            </tr>
          </tbody>
          <tfoot v-if="companyTotalRow">
            <tr class="border-t border-border bg-muted/30 font-semibold">
              <td class="px-4 py-3 text-foreground">{{ t('crm.salesPlans.companyTotal') }}</td>
              <td class="px-4 py-3 tabular-nums text-foreground">{{ companyTotalRow.target_count ?? '—' }}</td>
              <td class="px-4 py-3 tabular-nums text-foreground">{{ n(companyTotalRow.actual_count, 'decimal') }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-24 overflow-hidden rounded-full bg-muted">
                    <div class="h-full rounded-full transition-all" :class="progressBarClasses[companyTotalRow.status]" :style="{ width: progressBarWidth(companyTotalRow) }" />
                  </div>
                  <span class="whitespace-nowrap text-xs text-muted-foreground">
                    {{ companyTotalRow.target_count === null ? companyTotalRow.actual_count : `${companyTotalRow.actual_count} / ${companyTotalRow.target_count}` }}
                    <template v-if="companyTotalRow.percent !== null"> ({{ companyTotalRow.percent }}%)</template>
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="statusBadgeClasses[companyTotalRow.status]">
                  {{ t(`crm.salesPlans.status.${companyTotalRow.status}`) }}
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- EmployeeView -->
    <div v-else class="max-w-sm rounded-lg border border-border bg-surface p-5 shadow-card">
      <template v-if="employeeRows.length > 0 && employeeRows[0]">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.salesPlans.monthLabel') }}</p>

        <div class="mt-3 flex items-center gap-3">
          <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div class="h-full rounded-full transition-all" :class="progressBarClasses[employeeRows[0].status]" :style="{ width: progressBarWidth(employeeRows[0]) }" />
          </div>
          <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="statusBadgeClasses[employeeRows[0].status]">
            {{ t(`crm.salesPlans.status.${employeeRows[0].status}`) }}
          </span>
        </div>

        <p class="mt-2 text-lg font-semibold tabular-nums text-foreground">
          {{ employeeRows[0].target_count === null ? employeeRows[0].actual_count : `${employeeRows[0].actual_count} / ${employeeRows[0].target_count}` }}
          <template v-if="employeeRows[0].percent !== null">
            <span class="text-sm font-normal text-muted-foreground">({{ employeeRows[0].percent }}%)</span>
          </template>
        </p>

        <p v-if="employeeRows[0].target_count === null" class="mt-1 text-sm text-muted-foreground">{{ t('crm.salesPlans.noPlanAssigned') }}</p>
      </template>
    </div>

    <!-- ErrorAlert -->
    <div
      v-if="salesPlanStore.error"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ salesPlanStore.error }}</span>
    </div>
  </div>
</template>
