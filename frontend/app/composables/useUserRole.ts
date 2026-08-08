export function useUserRole() {
  const authStore = useAuthStore()
  const role = computed(() => authStore.user?.role ?? null)

  return {
    isOwner: computed<boolean>(() => role.value === 'owner'),
    isCoFounder: computed<boolean>(() => role.value === 'co_founder'),
    isEmployee: computed<boolean>(() => role.value === 'employee'),
    // Owner-equivalent access — every previously owner-only surface EXCEPT
    // co-founder role assignment and co-founder account deactivation, which
    // stay on isOwner strictly.
    isCompanyAdmin: computed<boolean>(() => role.value === 'owner' || role.value === 'co_founder'),
  }
}
