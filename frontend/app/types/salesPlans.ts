export type SalesPlanStatus = 'no_plan' | 'in_progress' | 'completed'

// One row of GET /sales-plans — either a real employee's plan/progress, or
// (owner only, always last) the synthetic company-wide aggregate row with
// every employee_* field null and is_company_total=true.
export interface SalesPlanProgress {
    sales_plan_id: number | null
    employee_id: number | null
    employee_first_name: string | null
    employee_last_name: string | null
    employee_email: string | null
    is_company_total: boolean

    target_count: number | null
    actual_count: number
    percent: number | null
    status: SalesPlanStatus
}

export interface SalesPlanUpsertInput {
    employee_id: number
    month: string
    target_count: number
}
