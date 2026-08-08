import type { SalesPlanStatus } from '~/types/salesPlans'
import type { CompanyRole } from '~/types/user'

export interface Employee {
    id: number
    email: string
    role: CompanyRole | null
    is_active: boolean
    first_name: string | null
    last_name: string | null
    phone: string | null
    social_links: string[]
    position_id: number | null
    created_at: string
}

export interface EmployeeUpdateInput {
    first_name?: string
    last_name?: string
    phone?: string
    social_links?: string[]
    position_id?: number | null
    is_active?: boolean
}

export interface EmployeeRoleUpdateInput {
    role: 'co_founder' | 'employee'
}

export interface EmployeeFormValues {
    first_name?: string
    last_name?: string
    phone?: string
    social_links: string[]
    position_id?: number | null
}

export interface EmployeeCurrentMonthPlan {
    target_count: number | null
    actual_count: number
    percent: number | null
    status: SalesPlanStatus
}

// Owner-only performance summary — see GET /employees/{id}/stats.
export interface EmployeeStats {
    started_at: string
    total_sold_count: number
    average_check: number | null
    total_profit_brought: number
    current_month_plan: EmployeeCurrentMonthPlan
    plans_completed_count: number
    plans_missed_count: number
    efficiency_rate: number | null
}
