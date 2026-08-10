<script setup lang="ts">
import { ExclamationTriangleIcon, UserGroupIcon } from '@heroicons/vue/24/outline'
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'
import type { InvitePreview } from '~/types/employeeInvites'

definePageMeta({ layout: 'auth' })

const { t, locale } = useI18n()
const validators = createValidators(t)

const errorMessage = ref('')
const isSubmitting = ref(false)
const showCheckEmailScreen = ref(false)
const registeredEmail = ref('')

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const inviteToken = computed<string | undefined>(() => typeof route.query.invite === 'string' ? route.query.invite : undefined)

const invitePreview = ref<InvitePreview | null>(null)
const isInviteInvalid = ref(false)

if (inviteToken.value) {
  const { apiGet } = useApi()
  try {
    invitePreview.value = await apiGet<InvitePreview>(`/invites/${inviteToken.value}`)
  } catch {
    isInviteInvalid.value = true
  }
}

// An invite fully determines company/role — the business-account checkbox
// only matters when registering without one.
const isForcedBusiness = computed<boolean>(() => route.query.type === 'business' && !inviteToken.value)
const isBusinessAccount = ref(isForcedBusiness.value)

const { meta, handleSubmit } = useForm()

const { value: email, errorMessage: emailError } = useField<string>('email', validators.email, { initialValue: '' })
const { value: password, errorMessage: passwordError } = useField<string>('password', validators.minLength(8), { initialValue: '' })

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const { requiresEmailConfirmation } = await authStore.register(
      values.email,
      values.password,
      isBusinessAccount.value ? 'business' : 'individual',
      inviteToken.value,
      locale.value
    )

    if (requiresEmailConfirmation) {
      registeredEmail.value = values.email
      showCheckEmailScreen.value = true
    } else {
      // A soft onboarding nudge — an invited employee lands straight on
      // Settings to fill in their own profile, but nothing else is blocked;
      // this only fires right after this one registration, never on later logins.
      router.push(inviteToken.value ? '/settings' : getPostAuthRedirectPath(authStore.user?.company_id))
    }
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
      <h2 v-if="isForcedBusiness" class="mb-4 text-center text-lg font-semibold text-foreground">
        {{ t('auth.register.businessHeading') }}
      </h2>

      <!-- InviteBanner -->
      <div
        v-if="invitePreview"
        class="mb-4 flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm text-foreground"
      >
        <UserGroupIcon class="mt-0.5 size-4 shrink-0 text-primary" />
        <span>
          {{ t('auth.register.inviteBanner', { company: invitePreview.company_name || '—' }) }}
          <template v-if="invitePreview.position_name">
            {{ t('auth.register.invitePosition', { position: invitePreview.position_name }) }}
          </template>
        </span>
      </div>

      <!-- InviteInvalidBanner -->
      <div
        v-else-if="isInviteInvalid"
        class="mb-4 flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <div>
          <p>{{ t('auth.register.inviteInvalid') }}</p>
          <NuxtLink to="/register" class="font-medium underline">{{ t('auth.register.regularRegisterLink') }}</NuxtLink>
        </div>
      </div>

      <form v-if="!isInviteInvalid" class="space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="email">{{ t('auth.register.emailLabel') }} <RequiredMark /></label>
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
          <label class="block text-sm font-medium text-foreground" for="password">{{ t('auth.register.passwordLabel') }} <RequiredMark /></label>
          <PasswordInput
            id="password"
            v-model="password"
            autocomplete="new-password"
            aria-required="true"
            :aria-invalid="!!passwordError"
          />
          <p v-if="passwordError" class="mt-1 text-xs text-destructive">{{ passwordError }}</p>
        </div>

        <!-- BusinessAccountCheckbox: hidden entirely when joining via invite —
             company/role are already fully determined by the invite token. -->
        <label v-if="!isForcedBusiness && !inviteToken" class="flex items-center gap-2 text-sm text-foreground">
          <input
            v-model="isBusinessAccount"
            type="checkbox"
            class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
          >
          {{ t('auth.register.businessCheckbox') }}
        </label>

        <!-- ErrorAlert -->
        <div
          v-if="errorMessage"
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
          {{ isSubmitting ? t('auth.register.submitting') : t('auth.register.submit') }}
        </button>

        <p class="text-center text-sm text-muted-foreground">
          {{ t('auth.register.hasAccount') }}
          <NuxtLink to="/login" class="font-medium text-primary hover:underline">{{ t('auth.register.loginLink') }}</NuxtLink>
        </p>
      </form>
    </template>

    <!-- CheckEmailScreen: shown instead of the form once a fresh
         business/owner registration has triggered a confirmation email. -->
    <div v-else class="space-y-4 text-center">
      <h2 class="text-lg font-semibold text-foreground">{{ t('auth.confirmEmail.checkEmailTitle') }}</h2>
      <p class="text-sm text-muted-foreground">{{ t('auth.confirmEmail.checkEmailBody', { email: registeredEmail }) }}</p>
      <ResendConfirmationButton :email="registeredEmail" />
    </div>
  </div>
</template>
