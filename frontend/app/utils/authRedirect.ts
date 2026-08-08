export function getPostAuthRedirectPath(companyId: number | null | undefined): string {
  return companyId != null ? '/crm' : '/garage'
}
