<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const validators = createValidators(t)

const errorMessage = ref('')
const unconfirmedEmail = ref('')
const isSubmitting = ref(false)

const authStore = useAuthStore()
const router = useRouter()

const { meta, handleSubmit } = useForm()

const { value: email, errorMessage: emailError } = useField<string>('email', validators.email, { initialValue: '' })
const { value: password, errorMessage: passwordError } = useField<string>('password', validators.required, { initialValue: '' })

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  unconfirmedEmail.value = ''
  isSubmitting.value = true

  try {
    await authStore.login(values.email, values.password)
    router.push(getPostAuthRedirectPath())
  } catch (error) {
    const apiError = error as ApiError
    if (apiError.code === 'email_not_confirmed') {
      unconfirmedEmail.value = apiError.email ?? values.email
    } else {
      errorMessage.value = apiError.message
    }
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <form class="space-y-4" @submit.prevent="onSubmit">
    <div>
      <label class="block text-sm font-medium text-foreground" for="email">{{ t('auth.login.emailLabel') }} <RequiredMark /></label>
      <input
        id="email"
        v-model="email"
        type="email"
        autocomplete="email"
        aria-required="true"
        :aria-invalid="!!emailError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="emailError" class="mt-1 text-xs text-destructive">{{ emailError }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="password">{{ t('auth.login.passwordLabel') }} <RequiredMark /></label>
      <PasswordInput
        id="password"
        v-model="password"
        autocomplete="current-password"
        aria-required="true"
        :aria-invalid="!!passwordError"
      />
      <p v-if="passwordError" class="mt-1 text-xs text-destructive">{{ passwordError }}</p>
      <p class="mt-1.5 text-right">
        <NuxtLink to="/auth/forgot-password" class="text-xs font-medium text-primary hover:underline">{{ t('auth.forgotPassword.loginLinkText') }}</NuxtLink>
      </p>
    </div>

    <!-- UnconfirmedEmailBlock -->
    <div
      v-if="unconfirmedEmail"
      class="flex flex-col gap-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm text-foreground"
      role="alert"
    >
      <div>
        <p class="font-medium">{{ t('auth.confirmEmail.loginBlockTitle') }}</p>
        <p class="text-muted-foreground">{{ t('auth.confirmEmail.loginBlockBody', { email: unconfirmedEmail }) }}</p>
      </div>
      <ResendConfirmationButton :email="unconfirmedEmail" />
    </div>

    <!-- ErrorAlert -->
    <div
      v-else-if="errorMessage"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>

    <button
      type="submit"
      :disabled="isSubmitting || !meta.valid"
      class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
      {{ isSubmitting ? t('auth.login.submitting') : t('auth.login.submit') }}
    </button>

    <p class="text-center text-sm text-muted-foreground">
      {{ t('auth.login.noAccount') }}
      <NuxtLink to="/register" class="font-medium text-primary hover:underline">{{ t('auth.login.registerLink') }}</NuxtLink>
    </p>
  </form>
</template>
