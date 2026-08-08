interface EmployeeNameSource {
    first_name: string | null
    last_name: string | null
}

// Prefers first_name/last_name (filled in on the employee's profile); falls
// back to email since name fields are optional and may not be set yet.
export function getEmployeeDisplayName(employee: EmployeeNameSource | null | undefined, fallbackEmail?: string | null): string | undefined {
    if (!employee) {
        return fallbackEmail ?? undefined
    }

    const fullName = [employee.first_name, employee.last_name].filter(Boolean).join(' ').trim()
    return fullName || fallbackEmail || undefined
}
