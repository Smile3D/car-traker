import type { TelegramConnectInput, TelegramPublishOutput, TelegramStatus } from '~/types/telegramIntegration'
import type { ApiError } from '~/composables/useApi'

export const useTelegramIntegrationStore = defineStore('telegramIntegration', () => {
    const isConnected = ref(false)
    const channelId = ref<string | null>(null)
    const connectedAt = ref<string | null>(null)
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const { apiGet, apiPost, apiDelete } = useApi()

    function applyStatus(status: TelegramStatus): void {
        isConnected.value = status.is_connected
        channelId.value = status.channel_id
        connectedAt.value = status.created_at
    }

    const fetchStatus = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            applyStatus(await apiGet<TelegramStatus>('/integrations/social/telegram/status'))
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            isLoading.value = false
        }
    }

    const connect = async (connectInput: TelegramConnectInput): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            applyStatus(await apiPost<TelegramStatus>('/integrations/social/telegram/connect', connectInput))
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const disconnect = async (): Promise<void> => {
        isLoading.value = true
        error.value = null
        try {
            await apiDelete<void>('/integrations/social/telegram/disconnect')
            isConnected.value = false
            channelId.value = null
            connectedAt.value = null
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    const publish = async (text: string): Promise<TelegramPublishOutput> => {
        isLoading.value = true
        error.value = null
        try {
            return await apiPost<TelegramPublishOutput>('/integrations/social/telegram/publish', { text })
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        isConnected,
        channelId,
        connectedAt,
        isLoading,
        error,
        fetchStatus,
        connect,
        disconnect,
        publish
    }
})
