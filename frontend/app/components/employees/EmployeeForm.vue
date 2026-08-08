<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { vMaska } from 'maska/vue'
import { useField, useForm } from 'vee-validate'
import type { Employee, EmployeeFormValues } from '~/types/employees'

const props = withDefaults(defineProps<{
  initialEmployee?: Employee
  submitLabel: string
  submittingLabel: string
  showCancelButton?: boolean
  cancelLabel?: string
}>(), {
  showCancelButton: false,
})

const emit = defineEmits<{ submit: [values: EmployeeFormValues], cancel: [] }>()

const { t } = useI18n()
const validators = createValidators(t)

const employeeStore = useEmployeeStore()
const positionStore = usePositionStore()

const { meta, handleSubmit } = useForm()

const { value: firstName } = useField<string>('first_name', undefined, { initialValue: props.initialEmployee?.first_name ?? '' })
const { value: lastName } = useField<string>('last_name', undefined, { initialValue: props.initialEmployee?.last_name ?? '' })
const { value: phone, errorMessage: phoneError } = useField<string>('phone', validators.optionalUkrainianPhone, { initialValue: props.initialEmployee?.phone ?? '' })
const { value: positionId } = useField<number | ''>('position_id', undefined, { initialValue: props.initialEmployee?.position_id ?? '' })

const socialLinks = ref<string[]>(
  props.initialEmployee?.social_links.length ? [...props.initialEmployee.social_links] : ['']
)

const submitForm = handleSubmit(() => {
  emit('submit', {
    first_name: firstName.value || undefined,
    last_name: lastName.value || undefined,
    phone: phone.value || undefined,
    social_links: socialLinks.value.map((link) => link.trim()).filter(Boolean),
    position_id: positionId.value === '' ? null : Number(positionId.value),
  })
})
</script>

<template>
  <form class="space-y-4" @submit.prevent="submitForm">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <label class="block text-sm font-medium text-foreground" for="employee-first-name">{{ t('crm.employees.form.firstNameLabel') }}</label>
        <input
          id="employee-first-name"
          v-model="firstName"
          type="text"
          :placeholder="t('crm.employees.form.firstNamePlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="employee-last-name">{{ t('crm.employees.form.lastNameLabel') }}</label>
        <input
          id="employee-last-name"
          v-model="lastName"
          type="text"
          :placeholder="t('crm.employees.form.lastNamePlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="employee-phone">{{ t('crm.employees.form.phoneLabel') }}</label>
      <input
        id="employee-phone"
        v-model="phone"
        v-maska="'+380 ## ### ## ##'"
        type="tel"
        :placeholder="t('crm.employees.form.phonePlaceholder')"
        :aria-invalid="!!phoneError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="phoneError" class="mt-1 text-xs text-destructive">{{ phoneError }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="employee-position">{{ t('crm.employees.form.positionLabel') }}</label>
      <select
        id="employee-position"
        v-model="positionId"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">{{ t('crm.employees.form.positionNotAssigned') }}</option>
        <option v-for="position in positionStore.positions" :key="position.id" :value="position.id">
          {{ position.name }}
        </option>
      </select>
    </div>

    <SocialLinksListInput
      v-model="socialLinks"
      :label="t('crm.employees.form.socialLinksLabel')"
      :placeholder="t('crm.employees.form.socialLinksPlaceholder')"
      :add-button-label="t('crm.employees.form.addSocialLinkButton')"
    />

    <div
      v-if="employeeStore.error"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ employeeStore.error }}</span>
    </div>

    <div class="flex justify-end gap-2 border-t border-border pt-4">
      <button
        v-if="showCancelButton"
        type="button"
        class="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
        @click="emit('cancel')"
      >
        {{ cancelLabel }}
      </button>
      <button
        type="submit"
        :disabled="employeeStore.isLoading || !meta.valid"
        class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ employeeStore.isLoading ? submittingLabel : submitLabel }}
      </button>
    </div>
  </form>
</template>
