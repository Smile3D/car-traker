import type { Employee, EmployeeRoleUpdateInput, EmployeeStats, EmployeeUpdateInput } from '~/types/employees'
import type { ApiError } from '~/composables/useApi'

export const useEmployeeStore = defineStore('employee', () => {
    const employees = ref<Employee[]>([])
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    // Keyed cache, populated lazily (only when a stats card is actually
    // expanded — see EmployeeDetailsReadOnly.vue) rather than fetched for
    // every employee up front, so opening the roster never fires N stats
    // requests at once.
    const statsByEmployeeId = reactive<Record<number, EmployeeStats>>({})

    const { apiGet, apiPatch } = useApi()

    // Always fetches the COMPLETE list (active and inactive together) so the
    // employees page can show both, and any other consumer (e.g. the client
    // assignment dropdown) can filter to active ones locally — mirroring the
    // full-list pattern used by clientStore/listingStore.
    const fetchEmployees = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            employees.value = await apiGet<Employee[]>('/employees?include_inactive=true')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const updateEmployee = async (employeeId: number, employeeInput: EmployeeUpdateInput): Promise<Employee> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedEmployee = await apiPatch<Employee>(`/employees/${employeeId}`, employeeInput)
            employees.value = employees.value.map((employee) => employee.id === employeeId ? updatedEmployee : employee)
            return updatedEmployee
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const updateEmployeeRole = async (employeeId: number, role: EmployeeRoleUpdateInput['role']): Promise<Employee> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedEmployee = await apiPatch<Employee>(`/employees/${employeeId}/role`, { role })
            employees.value = employees.value.map((employee) => employee.id === employeeId ? updatedEmployee : employee)
            return updatedEmployee
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    // No shared loading/error state here on purpose — several stats cards
    // can be expanded at once, and a shared ref would make one card's error
    // bleed into another's. Callers (EmployeeDetailsReadOnly.vue) track
    // their own local isLoading/error around this call.
    const fetchEmployeeStats = async (employeeId: number): Promise<EmployeeStats> => {
        const stats = await apiGet<EmployeeStats>(`/employees/${employeeId}/stats`)
        statsByEmployeeId[employeeId] = stats
        return stats
    }

    return {
        employees,
        isLoading,
        error,
        statsByEmployeeId,
        fetchEmployees,
        updateEmployee,
        updateEmployeeRole,
        fetchEmployeeStats
    }
})
