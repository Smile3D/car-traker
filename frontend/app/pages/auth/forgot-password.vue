<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t, locale } = useI18n()
const validators = createValidators(t)

const errorMessage = ref('')
const isSubmitting = ref(false)
const showCheckEmailScreen = ref(false)

const authStore = useAuthStore()

const { meta, handleSubmit } = useForm()
const { value: email, errorMessage: emailError } = useField<string>('email', validators.email, { initialValue: '' })

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    await authStore.forgotPassword(values.email, locale.value)
    showCheckEmailScreen.value = true
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <div>
    <template v-if="!showCheckEmailScreen">
      <h2 class="mb-4 text-center text-lg font-semibold text-foreground">{{ t('auth.forgotPassword.title') }}</h2>
      <p class="mb-4 text-center text-sm text-muted-foreground">{{ t('auth.forgotPassword.body') }}</p>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="email">{{ t('auth.forgotPassword.emailLabel') }} <RequiredMark /></label>
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

        <div
          v-if="errorMessage"
          class="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          :disabled="isSubmitting || !meta.valid"
          class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          {{ isSubmitting ? t('auth.forgotPassword.submitting') : t('auth.forgotPassword.submit') }}
        </button>

        <p class="text-center text-sm text-muted-foreground">
          <NuxtLink to="/login" class="font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
        </p>
      </form>
    </template>

    <div v-else class="space-y-4 text-center">
      <h2 class="text-lg font-semibold text-foreground">{{ t('auth.forgotPassword.checkEmailTitle') }}</h2>
      <p class="text-sm text-muted-foreground">{{ t('auth.forgotPassword.checkEmailBody') }}</p>
      <NuxtLink to="/login" class="text-sm font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
    </div>
  </div>
</template>
