import type { Client } from '~/types/clients'

// 'me' and 'unassigned' are quick shortcuts alongside picking specific
// employees by id — all combinable (OR'd together), mirroring Jira-style
// multi-select filters.
export type EmployeeFilterToken = 'me' | 'unassigned' | number

export function clientMatchesEmployeeFilter(
  client: Client,
  filterTokens: EmployeeFilterToken[],
  currentUserId: number | undefined
): boolean {
  if (filterTokens.length === 0) {
    return true
  }

  return filterTokens.some((token) => {
    if (token === 'me') {
      return currentUserId !== undefined && client.employee_id === currentUserId
    }
    if (token === 'unassigned') {
      return client.employee_id === null
    }
    return client.employee_id === token
  })
}
