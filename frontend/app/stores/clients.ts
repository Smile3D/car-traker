import type { Client, ClientCreateInput, ClientUpdateInput } from '~/types/clients'
import type { ApiError } from '~/composables/useApi'

export const useClientStore = defineStore('client', () => {
    const clients = ref<Client[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch, apiDelete } = useApi()

    // Always fetches the COMPLETE list (sellers and buyers together).
    // clientStore.clients is the single source of truth for both Kanban
    // boards — filtering by client_type/stage must happen locally over
    // this full list, never via a separate filtered server request.
    const fetchClients = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            clients.value = await apiGet<Client[]>('/clients')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    // Scoped to a single employee (the "Переглянути клієнтів" modal on the
    // Employees page) — deliberately does NOT touch `clients`, which stays
    // the full board dataset shared by the Kanban/List views; the caller
    // holds onto the returned array itself instead.
    const fetchClientsByEmployee = async (employeeId: number): Promise<Client[]> => {
        isLoading.value = true
        error.value = null
        try {
            return await apiGet<Client[]>(`/clients?employee_id=${employeeId}`)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const createClient = async (clientInput: ClientCreateInput): Promise<Client> => {
        isLoading.value = true
        error.value = null
        try {
            const createdClient = await apiPost<Client>('/clients', clientInput)
            clients.value.push(createdClient)
            return createdClient
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateClient = async (clientId: number, clientInput: ClientUpdateInput): Promise<Client> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedClient = await apiPatch<Client>(`/clients/${clientId}`, clientInput)
            clients.value = clients.value.map((client) => client.id === clientId ? updatedClient : client)
            return updatedClient
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const deleteClient = async (clientId: number, reason?: string): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>(`/clients/${clientId}`, reason ? { reason } : undefined)
            clients.value = clients.value.filter((client) => client.id !== clientId)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        clients,
        isLoading,
        error,
        fetchClients,
        fetchClientsByEmployee,
        createClient,
        updateClient,
        deleteClient
    }
})
