export default defineNuxtRouteMiddleware(() => {
  const authStore = useAuthStore()

  if (!authStore.user?.company_id) {
    return navigateTo('/settings')
  }
})
