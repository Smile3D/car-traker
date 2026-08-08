export interface TelegramStatus {
    is_connected: boolean
    channel_id: string | null
    created_at: string | null
}

export interface TelegramConnectInput {
    bot_token: string
    channel_id: string
}

export interface TelegramPublishOutput {
    message_id: number
}