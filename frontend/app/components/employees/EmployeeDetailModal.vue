<script setup lang="ts">
import { PencilSquareIcon } from '@heroicons/vue/24/outline'
import type { Employee, EmployeeFormValues } from '~/types/employees'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ employee: Employee }>()

const emit = defineEmits<{ close: [], 'view-clients': [] }>()

const { t } = useI18n()

const employeeStore = useEmployeeStore()

// Editing another employee's profile or deactivating/reactivating them is
// owner/co-founder-only — any company member can open this modal to view,
// but only the owner or a co-founder gets the management actions below.
const { isOwner, isCompanyAdmin } = useUserRole()

// Deactivating/reactivating a co-founder's account is strictly owner-only —
// a co-founder can manage a plain employee's account but not another
// co-founder's, mirroring the backend guard in update_employee.
const canToggleThisEmployeeActive = computed<boolean>(() =>
  isOwner.value || props.employee.role !== 'co_founder'
)

const isEditMode = ref(false)
const isDeactivateConfirmOpen = ref(false)
const isPromoteConfirmOpen = ref(false)
const isDemoteConfirmOpen = ref(false)

const displayName = computed<string>(() => getEmployeeDisplayName(props.employee, props.employee.email) ?? props.employee.email)

async function handleSubmit(values: EmployeeFormValues): Promise<void> {
  try {
    await employeeStore.updateEmployee(props.employee.id, values)
    isEditMode.value = false
  } catch {
    // ошибка уже сохранена в employeeStore.error и показана в форме
  }
}

async function handleDeactivateConfirm(): Promise<void> {
  await employeeStore.updateEmployee(props.employee.id, { is_active: false })
  isDeactivateConfirmOpen.value = false
}

async function handleReactivate(): Promise<void> {
  await employeeStore.updateEmployee(props.employee.id, { is_active: true })
}

async function handlePromoteConfirm(): Promise<void> {
  await employeeStore.updateEmployeeRole(props.employee.id, 'co_founder')
  isPromoteConfirmOpen.value = false
}

async function handleDemoteConfirm(): Promise<void> {
  await employeeStore.updateEmployeeRole(props.employee.id, 'employee')
  isDemoteConfirmOpen.value = false
}
</script>

<template>
  <BaseModal :title="displayName" @close="emit('close')">
    <div class="space-y-4">
      <EmployeeDetailsReadOnly v-if="!isEditMode" :employee="employee" @view-clients="emit('view-clients')" />
      <EmployeeForm
        v-else
        :initial-employee="employee"
        :submit-label="t('common.buttons.save')"
        :submitting-label="t('common.buttons.saving')"
        show-cancel-button
        :cancel-label="t('common.buttons.cancel')"
        @submit="handleSubmit"
        @cancel="isEditMode = false"
      />

      <div v-if="isCompanyAdmin" class="flex items-center justify-between border-t border-border pt-4">
        <button
          v-if="!isEditMode"
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isEditMode = true"
        >
          <PencilSquareIcon class="size-4" />
          {{ t('common.buttons.edit') }}
        </button>
        <span v-else />

        <button
          v-if="!isEditMode && employee.is_active && canToggleThisEmployeeActive"
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          @click="isDeactivateConfirmOpen = true"
        >
          {{ t('crm.employees.deactivateButton') }}
        </button>
        <button
          v-else-if="!isEditMode && canToggleThisEmployeeActive"
          type="button"
          class="flex items-center gap-1.5 rounded-md border border-success/30 px-3 py-1.5 text-sm font-medium text-success transition-colors hover:bg-success/10"
          @click="handleReactivate"
        >
          {{ t('crm.employees.reactivateButton') }}
        </button>
      </div>

      <div v-if="isOwner && !isEditMode" class="mt-2 flex justify-end">
        <button
          v-if="employee.role === 'employee'"
          type="button"
          class="rounded-md border border-primary/30 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/10"
          @click="isPromoteConfirmOpen = true"
        >
          {{ t('crm.employees.promoteToCoFounderButton') }}
        </button>
        <button
          v-else-if="employee.role === 'co_founder'"
          type="button"
          class="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isDemoteConfirmOpen = true"
        >
          {{ t('crm.employees.demoteCoFounderButton') }}
        </button>
      </div>
    </div>

    <ConfirmDialog
      v-if="isDeactivateConfirmOpen"
      :title="t('crm.employees.deactivateConfirmTitle')"
      :message="t('crm.employees.deactivateConfirmMessage')"
      :confirm-label="t('crm.employees.deactivateButton')"
      @confirm="handleDeactivateConfirm"
      @cancel="isDeactivateConfirmOpen = false"
    />
    <ConfirmDialog
      v-if="isPromoteConfirmOpen"
      :title="t('crm.employees.promoteConfirmTitle')"
      :message="t('crm.employees.promoteConfirmMessage')"
      :confirm-label="t('crm.employees.promoteToCoFounderButton')"
      @confirm="handlePromoteConfirm"
      @cancel="isPromoteConfirmOpen = false"
    />
    <ConfirmDialog
      v-if="isDemoteConfirmOpen"
      :title="t('crm.employees.demoteConfirmTitle')"
      :message="t('crm.employees.demoteConfirmMessage')"
      :confirm-label="t('crm.employees.demoteCoFounderButton')"
      @confirm="handleDemoteConfirm"
      @cancel="isDemoteConfirmOpen = false"
    />
  </BaseModal>
</template>
