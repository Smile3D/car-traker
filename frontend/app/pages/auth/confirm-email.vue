<script setup lang="ts">
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const status = ref<'verifying' | 'error'>('verifying')
const errorCode = ref('')
const manualEmail = ref('')

const tokenFromQuery = computed<string | undefined>(() => typeof route.query.token === 'string' ? route.query.token : undefined)

// Runs client-side only (never during SSR): confirmEmail() calls
// fetchCurrentUser() internally, which calls useApi() after crossing an
// await boundary — during SSR that loses Nuxt's app context. login()
// and register() never hit this because they only ever run from a
// client-side button click, never at page-load time.
onMounted(async () => {
  if (!tokenFromQuery.value) {
    status.value = 'error'
    errorCode.value = 'invalid'
    return
  }

  try {
    await authStore.confirmEmail(tokenFromQuery.value)
    router.push(getPostAuthRedirectPath(authStore.user?.company_id))
  } catch (error) {
    status.value = 'error'
    errorCode.value = (error as ApiError).code ?? 'invalid'
  }
})

const errorMessageKey = computed<string>(() => {
  if (errorCode.value === 'expired') return 'auth.confirmEmail.errorExpired'
  if (errorCode.value === 'already_used') return 'auth.confirmEmail.errorAlreadyUsed'
  return 'auth.confirmEmail.errorInvalid'
})
</script>

<template>
  <div class="space-y-4 text-center">
    <p v-if="status === 'verifying'" class="text-sm text-muted-foreground">{{ t('auth.confirmEmail.verifying') }}</p>

    <div v-else class="space-y-3">
      <p class="text-sm text-destructive">{{ t(errorMessageKey) }}</p>

      <div class="space-y-2 text-left">
        <label class="block text-sm font-medium text-foreground" for="manual-email">{{ t('auth.login.emailLabel') }}</label>
        <input
          id="manual-email"
          v-model="manualEmail"
          type="email"
          class="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p class="text-xs text-muted-foreground">{{ t('auth.confirmEmail.resendFormPrompt') }}</p>
        <ResendConfirmationButton v-if="manualEmail" :email="manualEmail" />
      </div>
    </div>
  </div>
</template>
