<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const validators = createValidators(t)
const route = useRoute()
const authStore = useAuthStore()

const tokenFromQuery = computed<string | undefined>(() => typeof route.query.token === 'string' ? route.query.token : undefined)

const status = ref<'form' | 'success' | 'error'>(tokenFromQuery.value ? 'form' : 'error')
const errorCode = ref(tokenFromQuery.value ? '' : 'invalid')
const isSubmitting = ref(false)

const { meta, handleSubmit } = useForm()
const { value: newPassword, errorMessage: newPasswordError } = useField<string>('newPassword', validators.minLength(8), { initialValue: '' })
const { value: confirmPassword, errorMessage: confirmPasswordError } = useField<string>('confirmPassword', validators.minLength(8), { initialValue: '' })

const passwordMismatch = computed<boolean>(() => Boolean(confirmPassword.value) && newPassword.value !== confirmPassword.value)

const errorMessageKey = computed<string>(() => {
  if (errorCode.value === 'expired') return 'auth.resetPassword.errorExpired'
  if (errorCode.value === 'already_used') return 'auth.resetPassword.errorAlreadyUsed'
  return 'auth.resetPassword.errorInvalid'
})

const onSubmit = handleSubmit(async (values) => {
  if (passwordMismatch.value || !tokenFromQuery.value) {
    return
  }

  isSubmitting.value = true
  try {
    await authStore.resetPassword(tokenFromQuery.value, values.newPassword)
    status.value = 'success'
  } catch (error) {
    status.value = 'error'
    errorCode.value = (error as ApiError).code ?? 'invalid'
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div v-if="status === 'success'" class="space-y-3 text-center">
      <p class="text-sm text-foreground">{{ t('auth.resetPassword.successMessage') }}</p>
      <NuxtLink to="/login" class="text-sm font-medium text-primary hover:underline">{{ t('auth.resetPassword.goToLoginLink') }}</NuxtLink>
    </div>

    <div v-else-if="status === 'error'" class="space-y-3 text-center">
      <p class="text-sm text-destructive">{{ t(errorMessageKey) }}</p>
      <NuxtLink to="/auth/forgot-password" class="text-sm font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
    </div>

    <form v-else class="space-y-4" @submit.prevent="onSubmit">
      <h2 class="text-center text-lg font-semibold text-foreground">{{ t('auth.resetPassword.title') }}</h2>

      <div>
        <label class="block text-sm font-medium text-foreground" for="new-password">{{ t('auth.resetPassword.newPasswordLabel') }} <RequiredMark /></label>
        <input
          id="new-password"
          v-model="newPassword"
          type="password"
          autocomplete="new-password"
          aria-required="true"
          :aria-invalid="!!newPasswordError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="newPasswordError" class="mt-1 text-xs text-destructive">{{ newPasswordError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="confirm-password">{{ t('auth.resetPassword.confirmPasswordLabel') }} <RequiredMark /></label>
        <input
          id="confirm-password"
          v-model="confirmPassword"
          type="password"
          autocomplete="new-password"
          aria-required="true"
          :aria-invalid="!!confirmPasswordError || passwordMismatch"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="passwordMismatch" class="mt-1 text-xs text-destructive">{{ t('auth.resetPassword.passwordMismatch') }}</p>
      </div>

      <button
        type="submit"
        :disabled="isSubmitting || !meta.valid || passwordMismatch"
        class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
        {{ isSubmitting ? t('auth.resetPassword.submitting') : t('auth.resetPassword.submit') }}
      </button>
    </form>
  </div>
</template>
