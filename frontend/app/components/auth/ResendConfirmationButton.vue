<script setup lang="ts">
import type { ApiError } from '~/composables/useApi'

const props = defineProps<{ email: string }>()

const COOLDOWN_SECONDS = 60

const authStore = useAuthStore()
const { t } = useI18n()

const isSending = ref(false)
const remainingSeconds = ref(0)
const errorMessage = ref('')
const successMessage = ref('')

let cooldownIntervalId: ReturnType<typeof setInterval> | undefined

function startCooldown(): void {
  remainingSeconds.value = COOLDOWN_SECONDS
  cooldownIntervalId = setInterval(() => {
    remainingSeconds.value -= 1
    if (remainingSeconds.value <= 0 && cooldownIntervalId) {
      clearInterval(cooldownIntervalId)
    }
  }, 1000)
}

onUnmounted(() => {
  if (cooldownIntervalId) {
    clearInterval(cooldownIntervalId)
  }
})

async function handleResend(): Promise<void> {
  errorMessage.value = ''
  successMessage.value = ''
  isSending.value = true

  try {
    await authStore.resendConfirmation(props.email)
    successMessage.value = t('auth.confirmEmail.resendSuccessMessage')
    startCooldown()
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div>
    <button
      type="button"
      :disabled="isSending || remainingSeconds > 0"
      class="text-sm font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50"
      @click="handleResend"
    >
      {{ remainingSeconds > 0 ? t('auth.confirmEmail.resendButtonCooldown', { seconds: remainingSeconds }) : t('auth.confirmEmail.resendButton') }}
    </button>
    <p v-if="successMessage" class="mt-1 text-xs text-muted-foreground">{{ successMessage }}</p>
    <p v-if="errorMessage" class="mt-1 text-xs text-destructive">{{ errorMessage }}</p>
  </div>
</template>
