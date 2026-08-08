import type { ClientLeadSource } from '~/utils/clientOptions'
import type { ClientType } from '~/utils/clientStages'

export interface ClientEmployeeSummary {
    id: number
    first_name: string | null
    last_name: string | null
    email: string
}

export interface Client {
    id: number
    company_id: number
    listing_id: number
    client_type: ClientType

    name: string
    phone: string
    email: string | null
    social_media: string | null

    stage_id: number
    employee_id: number | null
    employee: ClientEmployeeSummary | null
    notes: string | null
    lead_source: ClientLeadSource | null

    created_at: string
}

export interface ClientCreateInput {
    listing_id: number
    client_type: ClientType
    name: string
    phone: string
    email?: string
    social_media?: string
    stage_id?: number
    notes?: string
    lead_source?: ClientLeadSource
}

export interface ClientUpdateInput {
    name?: string
    phone?: string
    email?: string
    social_media?: string
    stage_id?: number
    employee_id?: number | null
    notes?: string
    lead_source?: ClientLeadSource | null
}

export interface ClientFormValues {
    name: string
    phone: string
    email?: string
    social_media?: string
    notes?: string
    listing_id?: number
    employee_id?: number | null
    lead_source?: ClientLeadSource
}

export interface ClientStage {
    id: number
    company_id: number
    client_type: ClientType
    name: string
    order: number
    created_at: string
}

export interface ClientStageCreateInput {
    client_type: ClientType
    name: string
}

export interface ClientStageUpdateInput {
    name: string
}
