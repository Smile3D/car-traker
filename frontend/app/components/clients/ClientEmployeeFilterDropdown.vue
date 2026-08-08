<script setup lang="ts">
import { ChevronDownIcon } from '@heroicons/vue/24/outline'
import type { Employee } from '~/types/employees'
import type { EmployeeFilterToken } from '~/utils/clientEmployeeFilter'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ employees: Employee[] }>()

const selectedTokens = defineModel<EmployeeFilterToken[]>({ default: () => [] })

const { t } = useI18n()

const isOpen = ref(false)
const rootElement = ref<HTMLElement | null>(null)

function handleDocumentClick(event: MouseEvent): void {
  if (rootElement.value && !rootElement.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onUnmounted(() => document.removeEventListener('click', handleDocumentClick))

function isSelected(token: EmployeeFilterToken): boolean {
  return selectedTokens.value.includes(token)
}

function toggleToken(token: EmployeeFilterToken): void {
  selectedTokens.value = isSelected(token)
    ? selectedTokens.value.filter((selectedToken) => selectedToken !== token)
    : [...selectedTokens.value, token]
}

function resetFilter(): void {
  selectedTokens.value = []
}

const triggerLabel = computed<string>(() =>
  selectedTokens.value.length > 0
    ? `${t('crm.clients.employeeFilter.triggerLabel')} (${selectedTokens.value.length})`
    : t('crm.clients.employeeFilter.triggerLabel')
)
</script>

<template>
  <div ref="rootElement" class="relative">
    <button
      type="button"
      class="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium transition-colors"
      :class="selectedTokens.length > 0 ? 'border-primary/40 bg-primary/5 text-primary' : 'text-foreground hover:bg-muted'"
      @click="isOpen = !isOpen"
    >
      {{ triggerLabel }}
      <ChevronDownIcon class="size-4" />
    </button>

    <div
      v-if="isOpen"
      class="absolute z-10 mt-1 w-64 rounded-md border border-border bg-surface py-1 shadow-elevated"
    >
      <button
        type="button"
        class="block w-full px-3 py-2 text-left text-sm hover:bg-muted"
        :class="selectedTokens.length === 0 ? 'font-semibold text-primary' : 'text-foreground'"
        @click="resetFilter"
      >
        {{ t('crm.clients.employeeFilter.allOption') }}
      </button>

      <div class="my-1 border-t border-border" />

      <label class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted">
        <input
          type="checkbox"
          class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
          :checked="isSelected('me')"
          @change="toggleToken('me')"
        >
        {{ t('crm.clients.employeeFilter.onlyMeOption') }}
      </label>

      <label class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted">
        <input
          type="checkbox"
          class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
          :checked="isSelected('unassigned')"
          @change="toggleToken('unassigned')"
        >
        {{ t('crm.clients.employeeFilter.unassignedOption') }}
      </label>

      <template v-if="employees.length > 0">
        <div class="my-1 border-t border-border" />

        <label
          v-for="employee in employees"
          :key="employee.id"
          class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted"
        >
          <input
            type="checkbox"
            class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
            :checked="isSelected(employee.id)"
            @change="toggleToken(employee.id)"
          >
          {{ getEmployeeDisplayName(employee, employee.email) }}
        </label>
      </template>

      <div class="my-1 border-t border-border" />

      <button
        type="button"
        class="block w-full px-3 py-2 text-left text-sm font-medium text-destructive hover:bg-destructive/10"
        :disabled="selectedTokens.length === 0"
        :class="selectedTokens.length === 0 ? 'cursor-not-allowed opacity-50' : ''"
        @click="resetFilter"
      >
        {{ t('crm.clients.employeeFilter.resetButton') }}
      </button>
    </div>
  </div>
</template>
