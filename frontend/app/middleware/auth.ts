export default defineNuxtRouteMiddleware(async () => {
  const authStore = useAuthStore()

  if (!authStore.isAuthenticated) {
    return navigateTo('/login')
  }

  if (!authStore.user) {
    try {
      await authStore.fetchCurrentUser()
    } catch {
      return navigateTo('/login')
    }
  }
})
