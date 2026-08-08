export type InviteStatus = 'active' | 'used' | 'revoked' | 'expired'

// What GET /invites/{token} returns — deliberately minimal (no email/token/
// company id), matching the backend's public, unauthenticated response.
export interface InvitePreview {
    company_name: string | null
    position_name: string | null
}

export interface EmployeeInvite {
    id: number
    email: string | null
    position_id: number | null
    created_at: string
    expires_at: string
    used_at: string | null
    is_revoked: boolean
    cancellation_reason: string | null
    // Present only while status === 'active' — once used/revoked/expired the
    // link is dead, so the backend stops returning it.
    token: string | null
    status: InviteStatus
}

export interface EmployeeInviteCreateInput {
    email?: string
    position_id?: number
}

export interface EmployeeInviteRevokeInput {
    cancellation_reason?: string
}

// Only returned once, right after creation — a freshly created invite is
// always active, so token is guaranteed non-null here.
export interface EmployeeInviteCreateResult extends EmployeeInvite {
    token: string
}
