type Translate = (key: string, params?: Record<string, unknown>) => string

export function createValidators(t: Translate) {
    const required = (value: unknown): true | string => {
        if (value === undefined || value === null || value === '') {
            return t('validation.required')
        }
        return true
    }

    const email = (value: string): true | string => {
        if (!value) {
            return t('validation.required')
        }
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || t('validation.invalidEmail')
    }

    const minLength = (min: number) => (value: string): true | string => {
        if (!value) {
            return t('validation.required')
        }
        return value.length >= min || t('validation.minLength', { min })
    }

    const numericString = (value: string): true | string => {
        if (!value) {
            return t('validation.required')
        }
        return /^\d+$/.test(value) || t('validation.numericValue')
    }

    const positiveNumber = (value: number | ''): true | string => {
        if (value === '' || value === undefined || value === null) {
            return t('validation.required')
        }
        return Number(value) > 0 || t('validation.positiveNumber')
    }

    const nonNegativeNumber = (value: number | ''): true | string => {
        if (value === '' || value === undefined || value === null) {
            return t('validation.required')
        }
        return Number(value) >= 0 || t('validation.nonNegativeNumber')
    }

    const optionalNonNegativeNumber = (value: number | ''): true | string => {
        if (value === '' || value === undefined || value === null) {
            return true
        }
        return Number(value) >= 0 || t('validation.nonNegativeNumber')
    }

    const optionalEmail = (value: string): true | string => {
        if (!value) {
            return true
        }
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || t('validation.invalidEmail')
    }

    const ukrainianPhone = (value: string): true | string => {
        if (!value) {
            return t('validation.required')
        }
        const normalizedPhone = value.replace(/[\s\-()]/g, '')
        return /^(\+380\d{9}|0\d{9})$/.test(normalizedPhone) || t('validation.invalidPhone')
    }

    const optionalUkrainianPhone = (value: string): true | string => {
        if (!value) {
            return true
        }
        const normalizedPhone = value.replace(/[\s\-()]/g, '')
        return /^(\+380\d{9}|0\d{9})$/.test(normalizedPhone) || t('validation.invalidPhone')
    }

    return {
        required,
        email,
        minLength,
        numericString,
        positiveNumber,
        nonNegativeNumber,
        optionalNonNegativeNumber,
        optionalEmail,
        ukrainianPhone,
        optionalUkrainianPhone
    }
}
