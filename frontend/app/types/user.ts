export type AccountType = 'individual' | 'business'
export type CompanyRole = 'owner' | 'co_founder' | 'employee'

export interface Company {
  id: number
  name: string | null
  business_phone: string | null
  business_tax_id: string | null
}

export interface User {
  id: number
  email: string
  account_type: AccountType
  company_id: number | null
  role: CompanyRole | null
  company: Company | null
  first_name: string | null
  last_name: string | null
  phone: string | null
  social_links: string[]
  avatar_url: string | null
  created_at: string
}

export interface BusinessProfileUpdateInput {
  company_name?: string
  business_phone?: string
  business_tax_id?: string
}

export interface OwnProfileUpdateInput {
  first_name?: string
  last_name?: string
  phone?: string
  social_links?: string[]
}
