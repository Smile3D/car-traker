<script setup lang="ts">
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { vMaska } from 'maska/vue'
import { useField, useForm } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'
import type { RateSource } from '~/types/currency'

definePageMeta({ middleware: 'auth' })

const { t, d } = useI18n()
const validators = createValidators(t)

const authStore = useAuthStore()
const telegramIntegrationStore = useTelegramIntegrationStore()
const currencyStore = useCurrencyStore()

// Company settings (profile + Telegram) are open to any company member —
// owner or employee. Employee management and Position management remain
// owner-only, but those live on separate pages, not here.
if (authStore.user?.company_id) {
  setPageLayout('business')
  await telegramIntegrationStore.fetchStatus()
}

const isCompanyMember = computed(() => Boolean(authStore.user?.company_id))
const { isCompanyAdmin } = useUserRole()

// Currency settings: editing (and even seeing this block) is owner/co-founder-only —
// simpler than a read-only variant for employees, and the effective rate is
// still visible to everyone via the header chip regardless.
if (isCompanyAdmin.value) {
  await currencyStore.fetchRate()
}

const rateSourceInput = ref<RateSource>(currencyStore.rate?.active_source ?? 'auto')
const manualRateInput = ref<string>(currencyStore.rate?.manual_rate != null ? String(currencyStore.rate.manual_rate) : '')

const isCurrencySubmitting = ref(false)
const currencyErrorMessage = ref('')
const isCurrencySaved = ref(false)

const formattedAutoRateUpdatedAt = computed<string | null>(() => {
  const updatedAt = currencyStore.rate?.auto_rate_updated_at
  return updatedAt ? d(new Date(updatedAt), 'shortWithTime') : null
})

async function handleCurrencySubmit(): Promise<void> {
  currencyErrorMessage.value = ''
  isCurrencySaved.value = false
  isCurrencySubmitting.value = true

  try {
    await currencyStore.updateSettings({
      rate_source: rateSourceInput.value,
      manual_rate: manualRateInput.value === '' ? undefined : Number(manualRateInput.value),
    })
    isCurrencySaved.value = true
  } catch (error) {
    currencyErrorMessage.value = (error as ApiError).message
  } finally {
    isCurrencySubmitting.value = false
  }
}

const companyName = ref(authStore.user?.company?.name ?? '')
const businessPhone = ref(authStore.user?.company?.business_phone ?? '')
const businessTaxId = ref(authStore.user?.company?.business_tax_id ?? '')

const isSubmitting = ref(false)
const errorMessage = ref('')
const isSaved = ref(false)

async function handleSubmit(): Promise<void> {
  errorMessage.value = ''
  isSaved.value = false
  isSubmitting.value = true

  try {
    await authStore.updateBusinessProfile({
      company_name: companyName.value || undefined,
      business_phone: businessPhone.value || undefined,
      business_tax_id: businessTaxId.value || undefined,
    })
    isSaved.value = true
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSubmitting.value = false
  }
}

// Own-profile section — available to every account type, unlike the company
// section above. Loads whatever's already saved (all nullable on a fresh
// account) rather than starting blank each time.
const { meta: profileMeta, handleSubmit: handleProfileSubmit } = useForm()

const { value: firstName, errorMessage: firstNameError } = useField<string>(
  'profile_first_name', validators.required, { initialValue: authStore.user?.first_name ?? '' }
)
const { value: lastName, errorMessage: lastNameError } = useField<string>(
  'profile_last_name', validators.required, { initialValue: authStore.user?.last_name ?? '' }
)
const { value: profilePhone, errorMessage: profilePhoneError } = useField<string>(
  'profile_phone', validators.ukrainianPhone, { initialValue: authStore.user?.phone ?? '' }
)

const profileSocialLinks = ref<string[]>(
  authStore.user?.social_links.length ? [...authStore.user.social_links] : ['']
)

const isProfileSubmitting = ref(false)
const profileErrorMessage = ref('')
const isProfileSaved = ref(false)

const submitProfileForm = handleProfileSubmit(async () => {
  profileErrorMessage.value = ''
  isProfileSaved.value = false
  isProfileSubmitting.value = true

  try {
    await authStore.updateOwnProfile({
      first_name: firstName.value,
      last_name: lastName.value,
      phone: profilePhone.value,
      social_links: profileSocialLinks.value.map((link) => link.trim()).filter(Boolean),
    })
    isProfileSaved.value = true
  } catch (error) {
    profileErrorMessage.value = (error as ApiError).message
  } finally {
    isProfileSubmitting.value = false
  }
})

// Avatar upload — same limits as the receipt/listing-photo uploads (see
// UploadReceiptModal.vue) and the same "preview locally, submit separately"
// flow: picking a file never uploads it immediately, only Save does.
const AVATAR_ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const AVATAR_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

const selectedAvatarFile = ref<File | null>(null)
const avatarPreviewUrl = ref<string | null>(null)
const avatarValidationError = ref<string | null>(null)
const avatarErrorMessage = ref('')
const isAvatarUploading = ref(false)
const isAvatarDeleting = ref(false)

function revokeAvatarPreview(): void {
  if (avatarPreviewUrl.value) {
    URL.revokeObjectURL(avatarPreviewUrl.value)
    avatarPreviewUrl.value = null
  }
}

function handleAvatarFileChange(fileChangeEvent: Event): void {
  const file = (fileChangeEvent.target as HTMLInputElement).files?.[0] ?? null
  avatarValidationError.value = null
  avatarErrorMessage.value = ''
  revokeAvatarPreview()
  selectedAvatarFile.value = null

  if (!file) {
    return
  }

  if (!AVATAR_ALLOWED_MIME_TYPES.includes(file.type)) {
    avatarValidationError.value = t('settings.myProfile.avatarErrorInvalidType')
    return
  }

  if (file.size > AVATAR_MAX_FILE_SIZE_BYTES) {
    avatarValidationError.value = t('settings.myProfile.avatarErrorTooLarge')
    return
  }

  selectedAvatarFile.value = file
  avatarPreviewUrl.value = URL.createObjectURL(file)
}

function handleAvatarCancelPreview(): void {
  revokeAvatarPreview()
  selectedAvatarFile.value = null
  avatarValidationError.value = null
}

async function handleAvatarUpload(): Promise<void> {
  if (!selectedAvatarFile.value) {
    return
  }

  avatarErrorMessage.value = ''
  isAvatarUploading.value = true
  try {
    await authStore.uploadAvatar(selectedAvatarFile.value)
    revokeAvatarPreview()
    selectedAvatarFile.value = null
  } catch (error) {
    avatarErrorMessage.value = (error as ApiError).message
  } finally {
    isAvatarUploading.value = false
  }
}

async function handleAvatarDelete(): Promise<void> {
  avatarErrorMessage.value = ''
  isAvatarDeleting.value = true
  try {
    await authStore.deleteAvatar()
  } catch (error) {
    avatarErrorMessage.value = (error as ApiError).message
  } finally {
    isAvatarDeleting.value = false
  }
}

onUnmounted(() => {
  revokeAvatarPreview()
})

const botToken = ref('')
const telegramChannelId = ref('')
const isConnectingTelegram = ref(false)
const telegramConnectError = ref('')
const isDisconnectConfirmOpen = ref(false)

async function handleTelegramConnect(): Promise<void> {
  telegramConnectError.value = ''
  isConnectingTelegram.value = true

  try {
    await telegramIntegrationStore.connect({
      bot_token: botToken.value,
      channel_id: telegramChannelId.value,
    })
    botToken.value = ''
    telegramChannelId.value = ''
  } catch (error) {
    telegramConnectError.value = (error as ApiError).message
  } finally {
    isConnectingTelegram.value = false
  }
}

async function handleTelegramDisconnect(): Promise<void> {
  await telegramIntegrationStore.disconnect()
  isDisconnectConfirmOpen.value = false
}
</script>

<template>
  <div class="mx-auto max-w-lg space-y-6">
    <h1 class="text-xl font-semibold text-foreground">{{ t('settings.title') }}</h1>

    <!-- MyProfileSection: available to every account type, unlike the two
         sections below which only apply to company members. -->
    <section class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card">
      <h2 class="text-base font-semibold text-foreground">{{ t('settings.myProfile.sectionTitle') }}</h2>

      <!-- AvatarSection -->
      <div class="space-y-2">
        <div class="flex items-center gap-4">
          <img
            v-if="avatarPreviewUrl"
            :src="avatarPreviewUrl"
            class="size-16 rounded-full object-cover"
            :alt="t('settings.myProfile.avatarPreviewAlt')"
          >
          <UserAvatar v-else size-class="size-16 text-lg" />

          <div class="flex flex-wrap items-center gap-2">
            <label
              for="profile-avatar-file"
              class="cursor-pointer rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
            >
              {{ t('settings.myProfile.uploadAvatarButton') }}
            </label>
            <input
              id="profile-avatar-file"
              type="file"
              accept="image/*"
              class="sr-only"
              @change="handleAvatarFileChange"
            >

            <template v-if="selectedAvatarFile">
              <button
                type="button"
                :disabled="isAvatarUploading"
                class="rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                @click="handleAvatarUpload"
              >
                {{ isAvatarUploading ? t('settings.myProfile.avatarUploading') : t('common.buttons.save') }}
              </button>
              <button
                type="button"
                :disabled="isAvatarUploading"
                class="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                @click="handleAvatarCancelPreview"
              >
                {{ t('common.buttons.cancel') }}
              </button>
            </template>

            <button
              v-else-if="authStore.user?.avatar_url"
              type="button"
              :disabled="isAvatarDeleting"
              class="rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-50"
              @click="handleAvatarDelete"
            >
              {{ isAvatarDeleting ? t('common.buttons.deleting') : t('settings.myProfile.removeAvatarButton') }}
            </button>
          </div>
        </div>

        <p v-if="avatarValidationError" class="text-xs text-destructive">{{ avatarValidationError }}</p>

        <!-- AvatarErrorAlert -->
        <div
          v-if="avatarErrorMessage"
          class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ avatarErrorMessage }}</span>
        </div>
      </div>

      <form class="space-y-4" @submit.prevent="submitProfileForm">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-foreground" for="profile-first-name">
              {{ t('settings.myProfile.firstNameLabel') }} <RequiredMark />
            </label>
            <input
              id="profile-first-name"
              v-model="firstName"
              type="text"
              :placeholder="t('settings.myProfile.firstNamePlaceholder')"
              aria-required="true"
              :aria-invalid="!!firstNameError"
              class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
            <p v-if="firstNameError" class="mt-1 text-xs text-destructive">{{ firstNameError }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-foreground" for="profile-last-name">
              {{ t('settings.myProfile.lastNameLabel') }} <RequiredMark />
            </label>
            <input
              id="profile-last-name"
              v-model="lastName"
              type="text"
              :placeholder="t('settings.myProfile.lastNamePlaceholder')"
              aria-required="true"
              :aria-invalid="!!lastNameError"
              class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
            <p v-if="lastNameError" class="mt-1 text-xs text-destructive">{{ lastNameError }}</p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="profile-phone">
            {{ t('settings.myProfile.phoneLabel') }} <RequiredMark />
          </label>
          <input
            id="profile-phone"
            v-model="profilePhone"
            v-maska="'+380 ## ### ## ##'"
            type="tel"
            :placeholder="t('settings.myProfile.phonePlaceholder')"
            aria-required="true"
            :aria-invalid="!!profilePhoneError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="profilePhoneError" class="mt-1 text-xs text-destructive">{{ profilePhoneError }}</p>
        </div>

        <SocialLinksListInput
          v-model="profileSocialLinks"
          :label="t('settings.myProfile.socialLinksLabel')"
          :placeholder="t('settings.myProfile.socialLinksPlaceholder')"
          :add-button-label="t('settings.myProfile.addSocialLinkButton')"
        />

        <!-- SuccessAlert -->
        <div
          v-if="isProfileSaved"
          class="flex items-start gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success"
          role="status"
        >
          <CheckCircleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ t('settings.myProfile.savedMessage') }}</span>
        </div>

        <!-- ErrorAlert -->
        <div
          v-if="profileErrorMessage"
          class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ profileErrorMessage }}</span>
        </div>

        <button
          type="submit"
          :disabled="isProfileSubmitting || !profileMeta.valid"
          class="flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ isProfileSubmitting ? t('common.buttons.saving') : t('common.buttons.save') }}
        </button>
      </form>
    </section>

    <section
      v-if="isCompanyMember"
      class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card"
    >
      <h2 class="text-base font-semibold text-foreground">{{ t('settings.businessSectionTitle') }}</h2>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="company-name">
            {{ t('settings.companyNameLabel') }}
          </label>
          <input
            id="company-name"
            v-model="companyName"
            type="text"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="business-phone">
            {{ t('settings.businessPhoneLabel') }}
          </label>
          <input
            id="business-phone"
            v-model="businessPhone"
            type="tel"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="business-tax-id">
            {{ t('settings.businessTaxIdLabel') }}
          </label>
          <input
            id="business-tax-id"
            v-model="businessTaxId"
            type="text"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
        </div>

        <!-- SuccessAlert -->
        <div
          v-if="isSaved"
          class="flex items-start gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success"
          role="status"
        >
          <CheckCircleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ t('settings.savedMessage') }}</span>
        </div>

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
          :disabled="isSubmitting"
          class="flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ isSubmitting ? t('common.buttons.saving') : t('common.buttons.save') }}
        </button>
      </form>
    </section>

    <!-- CurrencySection -->
    <section
      v-if="isCompanyAdmin"
      class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card"
    >
      <h2 class="text-base font-semibold text-foreground">{{ t('settings.currency.sectionTitle') }}</h2>

      <div class="rounded-md bg-muted px-3 py-2">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('settings.currency.autoRateLabel') }}</p>
        <p v-if="currencyStore.rate?.auto_rate != null" class="mt-0.5 text-sm font-semibold text-foreground">
          {{ t('nav.currencyRateDisplay', { rate: currencyStore.rate.auto_rate.toFixed(2) }) }}
          <span class="ml-1 text-xs font-normal text-muted-foreground">
            {{ t('settings.currency.autoRateUpdatedAt', { datetime: formattedAutoRateUpdatedAt }) }}
          </span>
        </p>
        <p v-else class="mt-0.5 text-sm text-muted-foreground">{{ t('settings.currency.autoRateUnavailable') }}</p>
      </div>

      <form class="space-y-4" @submit.prevent="handleCurrencySubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="manual-rate">
            {{ t('settings.currency.manualRateLabel') }}
          </label>
          <input
            id="manual-rate"
            v-model="manualRateInput"
            type="number"
            min="0"
            step="0.01"
            :placeholder="t('settings.currency.manualRatePlaceholder')"
            class="mt-1.5 w-full max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
        </div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm text-foreground">
            <input
              v-model="rateSourceInput"
              type="radio"
              value="auto"
              class="size-4 border-border text-primary focus:ring-1 focus:ring-primary"
            >
            {{ t('settings.currency.useAutoOption') }}
          </label>
          <label class="flex items-center gap-2 text-sm text-foreground">
            <input
              v-model="rateSourceInput"
              type="radio"
              value="manual"
              class="size-4 border-border text-primary focus:ring-1 focus:ring-primary"
            >
            {{ t('settings.currency.useManualOption') }}
          </label>
        </div>

        <!-- SuccessAlert -->
        <div
          v-if="isCurrencySaved"
          class="flex items-start gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success"
          role="status"
        >
          <CheckCircleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ t('settings.currency.savedMessage') }}</span>
        </div>

        <!-- ErrorAlert -->
        <div
          v-if="currencyErrorMessage"
          class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ currencyErrorMessage }}</span>
        </div>

        <button
          type="submit"
          :disabled="isCurrencySubmitting"
          class="flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ isCurrencySubmitting ? t('common.buttons.saving') : t('common.buttons.save') }}
        </button>
      </form>
    </section>

    <!-- TelegramSection -->
    <section
      v-if="isCompanyMember"
      id="telegram-section"
      class="space-y-4 rounded-lg border border-border bg-surface p-5 shadow-card"
    >
      <h2 class="text-base font-semibold text-foreground">{{ t('settings.telegram.title') }}</h2>

      <!-- ConnectedState -->
      <div v-if="telegramIntegrationStore.isConnected" class="space-y-4">
        <div class="flex items-start gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success" role="status">
          <CheckCircleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ t('settings.telegram.connectedStatus', { channel: telegramIntegrationStore.channelId }) }}</span>
        </div>

        <button
          type="button"
          class="rounded-md border border-destructive/30 px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          @click="isDisconnectConfirmOpen = true"
        >
          {{ t('settings.telegram.disconnectButton') }}
        </button>
      </div>

      <!-- DisconnectedState -->
      <div v-else class="space-y-4">
        <ol class="list-inside list-decimal space-y-1.5 text-sm text-muted-foreground">
          <li>{{ t('settings.telegram.step1') }}</li>
          <li>{{ t('settings.telegram.step2') }}</li>
          <li>{{ t('settings.telegram.step3') }}</li>
          <li>{{ t('settings.telegram.step4') }}</li>
          <li>{{ t('settings.telegram.step5') }}</li>
          <li>{{ t('settings.telegram.step6') }}</li>
        </ol>

        <form class="space-y-4" @submit.prevent="handleTelegramConnect">
          <div>
            <label class="block text-sm font-medium text-foreground" for="telegram-bot-token">
              {{ t('settings.telegram.botTokenLabel') }}
            </label>
            <PasswordInput
              id="telegram-bot-token"
              v-model="botToken"
              autocomplete="off"
              :placeholder="t('settings.telegram.botTokenPlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-foreground" for="telegram-channel-id">
              {{ t('settings.telegram.channelIdLabel') }}
            </label>
            <input
              id="telegram-channel-id"
              v-model="telegramChannelId"
              type="text"
              :placeholder="t('settings.telegram.channelIdPlaceholder')"
              class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
          </div>

          <!-- ErrorAlert -->
          <div
            v-if="telegramConnectError"
            class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
            role="alert"
          >
            <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
            <span>{{ telegramConnectError }}</span>
          </div>

          <button
            type="submit"
            :disabled="isConnectingTelegram || !botToken || !telegramChannelId"
            class="flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ isConnectingTelegram ? t('settings.telegram.connectingButton') : t('settings.telegram.connectButton') }}
          </button>
        </form>
      </div>
    </section>

    <ConfirmDialog
      v-if="isDisconnectConfirmOpen"
      :title="t('settings.telegram.disconnectConfirmTitle')"
      :message="t('settings.telegram.disconnectConfirmMessage')"
      :confirm-label="t('settings.telegram.disconnectButton')"
      @confirm="handleTelegramDisconnect"
      @cancel="isDisconnectConfirmOpen = false"
    />
  </div>
</template>
