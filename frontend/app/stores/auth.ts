import type { AccountType, BusinessProfileUpdateInput, OwnProfileUpdateInput, User } from '~/types/user'
import type { ApiError } from '~/composables/useApi'

interface TokenResponse {
  access_token: string
  token_type: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = useCookie<string | null>('auth_token', { sameSite: 'lax' })
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => Boolean(token.value))

  async function login(email: string, password: string): Promise<void> {
    const { apiPost } = useApi()
    const formBody = new URLSearchParams({ username: email, password })

    const tokenResponse = await apiPost<TokenResponse>('/auth/login', formBody)
    token.value = tokenResponse.access_token

    await fetchCurrentUser()
  }

  async function register(email: string, password: string, accountType: AccountType = 'individual', inviteToken?: string, locale?: string): Promise<{ requiresEmailConfirmation: boolean }> {
    const { apiPost } = useApi()
    await apiPost<User>('/auth/register', { email, password, account_type: accountType, invite_token: inviteToken, locale })

    // Only a fresh business/owner registration (no invite) requires
    // confirming the email before the account can be used — everything
    // else auto-logs-in immediately, same as before this feature.
    const requiresEmailConfirmation = accountType === 'business' && !inviteToken
    if (!requiresEmailConfirmation) {
      await login(email, password)
    }

    return { requiresEmailConfirmation }
  }

  async function confirmEmail(confirmationToken: string): Promise<void> {
    const { apiPost } = useApi()
    const tokenResponse = await apiPost<TokenResponse>('/auth/confirm-email', { token: confirmationToken })
    token.value = tokenResponse.access_token

    await fetchCurrentUser()
  }

  async function resendConfirmation(email: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/resend-confirmation', { email })
  }

  async function forgotPassword(email: string, locale?: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/forgot-password', { email, locale })
  }

  async function resetPassword(token: string, newPassword: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/reset-password', { token, new_password: newPassword })
  }

  async function fetchCurrentUser(): Promise<void> {
    const { apiGet } = useApi()

    try {
      user.value = await apiGet<User>('/auth/me')
    } catch (error) {
      if ((error as ApiError).statusCode === 401) {
        logout()
      }
      throw error
    }
  }

  async function updateBusinessProfile(businessProfileUpdate: BusinessProfileUpdateInput): Promise<void> {
    const { apiPatch } = useApi()
    user.value = await apiPatch<User>('/auth/me', businessProfileUpdate)
  }

  // Own-profile fields (name/phone/social links) — same /auth/me endpoint as
  // updateBusinessProfile, but distinct in that it applies to any logged-in
  // user regardless of company membership (see backend's update_current_user).
  async function updateOwnProfile(ownProfileUpdate: OwnProfileUpdateInput): Promise<void> {
    const { apiPatch } = useApi()
    user.value = await apiPatch<User>('/auth/me', ownProfileUpdate)
  }

  async function uploadAvatar(file: File): Promise<void> {
    const { apiPost } = useApi()
    const formData = new FormData()
    formData.append('file', file)
    user.value = await apiPost<User>('/auth/me/avatar', formData)
  }

  async function deleteAvatar(): Promise<void> {
    const { apiDelete } = useApi()
    user.value = await apiDelete<User>('/auth/me/avatar')
  }

  // Same blob-fetch pattern as receiptStore.fetchReceiptImageUrl — there's
  // no public static URL for uploaded files, /auth/me/avatar/file is an
  // authenticated endpoint returning the raw image.
  async function fetchAvatarImageUrl(): Promise<string> {
    const { apiGetBlob } = useApi()
    const imageBlob = await apiGetBlob('/auth/me/avatar/file')
    return URL.createObjectURL(imageBlob)
  }

  function logout(): void {
    token.value = null
    user.value = null
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    confirmEmail,
    resendConfirmation,
    forgotPassword,
    resetPassword,
    fetchCurrentUser,
    updateBusinessProfile,
    updateOwnProfile,
    uploadAvatar,
    deleteAvatar,
    fetchAvatarImageUrl,
    logout
  }
})
