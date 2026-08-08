import type {
    EmployeeInvite,
    EmployeeInviteCreateInput,
    EmployeeInviteCreateResult,
    EmployeeInviteRevokeInput
} from '~/types/employeeInvites'
import type { ApiError } from '~/composables/useApi'

export const useEmployeeInviteStore = defineStore('employeeInvite', () => {
    const invites = ref<EmployeeInvite[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiPatch } = useApi()

    const fetchInvites = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            invites.value = await apiGet<EmployeeInvite[]>('/employees/invites')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const createInvite = async (input: EmployeeInviteCreateInput): Promise<EmployeeInviteCreateResult> => {
        isLoading.value = true
        error.value = null
        try {
            const created = await apiPost<EmployeeInviteCreateResult>('/employees/invites', input)
            // Re-fetch rather than hand-construct the list entry: `status` is
            // server-computed (active/used/revoked/expired) and the list
            // view never needs the token this response carries.
            await fetchInvites()
            return created
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const revokeInvite = async (inviteId: number, revokeInput: EmployeeInviteRevokeInput = {}): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            const revoked = await apiPatch<EmployeeInvite>(`/employees/invites/${inviteId}/revoke`, revokeInput)
            invites.value = invites.value.map((invite) => invite.id === inviteId ? revoked : invite)
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        invites,
        isLoading,
        error,
        fetchInvites,
        createInvite,
        revokeInvite
    }
})
