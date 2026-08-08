<script setup lang="ts">
import type { Client } from '~/types/clients'
import type { Employee } from '~/types/employees'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = defineProps<{ employee: Employee }>()

const emit = defineEmits<{ close: [], 'select-client': [client: Client] }>()

const { t } = useI18n()

const clientStore = useClientStore()

const clients = ref<Client[]>([])
const isLoading = ref(true)

onMounted(async () => {
  try {
    clients.value = await clientStore.fetchClientsByEmployee(props.employee.id)
  } finally {
    isLoading.value = false
  }
})

const displayName = computed<string>(() => getEmployeeDisplayName(props.employee, props.employee.email) ?? props.employee.email)
const modalTitle = computed<string>(() => t('crm.employees.clientsModal.title', { name: displayName.value }))
</script>

<template>
  <BaseModal :title="modalTitle" max-width="lg" @close="emit('close')">
    <p v-if="isLoading" class="text-sm text-muted-foreground">{{ t('crm.employees.clientsModal.loading') }}</p>
    <ClientListView v-else :clients="clients" @select="(client) => emit('select-client', client)" />
  </BaseModal>
</template>
