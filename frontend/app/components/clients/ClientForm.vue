<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { vMaska } from 'maska/vue'
import { useField, useForm } from 'vee-validate'
import type { Client, ClientFormValues } from '~/types/clients'
import type { Employee } from '~/types/employees'
import type { Listing, ListingStatus } from '~/types/listings'
import { CLIENT_LEAD_SOURCES, type ClientLeadSource, getLeadSourceLabelKey } from '~/utils/clientOptions'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

const props = withDefaults(defineProps<{
  initialClient?: Client
  showListingSelector?: boolean
  showNotesField?: boolean
  showEmployeeField?: boolean
  submitLabel: string
  submittingLabel: string
  showCancelButton?: boolean
  cancelLabel?: string
}>(), {
  showListingSelector: false,
  showNotesField: false,
  showEmployeeField: false,
  showCancelButton: false,
})

const emit = defineEmits<{ submit: [values: ClientFormValues], cancel: [] }>()

const { t } = useI18n()
const validators = createValidators(t)

const clientStore = useClientStore()
const listingStore = useListingStore()
const employeeStore = useEmployeeStore()

// The currently assigned employee stays selectable even if they've since
// been deactivated, so an existing assignment is never silently hidden —
// every other option is restricted to active employees.
const assignableEmployees = computed<Employee[]>(() => {
  const activeEmployees = employeeStore.employees.filter((employee) => employee.is_active)
  const currentEmployeeId = props.initialClient?.employee_id
  if (currentEmployeeId != null && !activeEmployees.some((employee) => employee.id === currentEmployeeId)) {
    const currentEmployee = employeeStore.employees.find((employee) => employee.id === currentEmployeeId)
    if (currentEmployee) {
      return [...activeEmployees, currentEmployee]
    }
  }
  return activeEmployees
})

// This selector only ever backs buyer creation (the seller path creates its
// listing atomically via ListingForm, never through here) — adding a buyer
// to an already-closed deal makes no sense, so sold/removed listings are
// excluded, same set the Inventory page shows by default.
const nonArchivedStatuses: ListingStatus[] = ['draft', 'active', 'reserved']

// A listing can have at most one buyer (same one-per-listing cap as the
// seller) — listings that already have one are excluded here so the picker
// never offers a choice that would just 409 on submit.
const listingIdsWithBuyer = computed<Set<number>>(() =>
  new Set(clientStore.clients.filter((client) => client.client_type === 'buyer').map((client) => client.listing_id))
)

const availableListings = computed<Listing[]>(() =>
  listingStore.listings.filter((listing) =>
    nonArchivedStatuses.includes(listing.status) && !listingIdsWithBuyer.value.has(listing.id)
  )
)

const { meta, handleSubmit } = useForm()

const { value: name, errorMessage: nameError } = useField<string>('name', validators.minLength(2), { initialValue: props.initialClient?.name ?? '' })
const { value: phone, errorMessage: phoneError } = useField<string>('phone', validators.ukrainianPhone, { initialValue: props.initialClient?.phone ?? '' })
const { value: email, errorMessage: emailError } = useField<string>('email', validators.optionalEmail, { initialValue: props.initialClient?.email ?? '' })
const { value: socialMedia } = useField<string>('social_media', undefined, { initialValue: props.initialClient?.social_media ?? '' })
const { value: notes } = useField<string>('notes', undefined, { initialValue: props.initialClient?.notes ?? '' })
const { value: listingId, errorMessage: listingIdError } = useField<number | ''>(
  'listing_id',
  props.showListingSelector ? validators.required : undefined,
  { initialValue: props.initialClient?.listing_id ?? '' }
)
const { value: employeeId } = useField<number | ''>('employee_id', undefined, { initialValue: props.initialClient?.employee_id ?? '' })
const { value: leadSource } = useField<ClientLeadSource | ''>('lead_source', undefined, { initialValue: props.initialClient?.lead_source ?? '' })

const submitForm = handleSubmit(() => {
  emit('submit', {
    name: name.value,
    phone: phone.value,
    email: email.value || undefined,
    social_media: socialMedia.value || undefined,
    notes: props.showNotesField ? (notes.value || undefined) : undefined,
    listing_id: props.showListingSelector ? Number(listingId.value) : undefined,
    employee_id: props.showEmployeeField ? (employeeId.value === '' ? null : Number(employeeId.value)) : undefined,
    lead_source: leadSource.value || undefined,
  })
})
</script>

<template>
  <form class="space-y-4" @submit.prevent="submitForm">
    <div>
      <label class="block text-sm font-medium text-foreground" for="client-name">{{ t('crm.clients.form.nameLabel') }} <RequiredMark /></label>
      <input
        id="client-name"
        v-model="name"
        type="text"
        :placeholder="t('crm.clients.form.namePlaceholder')"
        aria-required="true"
        :aria-invalid="!!nameError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="nameError" class="mt-1 text-xs text-destructive">{{ nameError }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="client-phone">{{ t('crm.clients.form.phoneLabel') }} <RequiredMark /></label>
      <input
        id="client-phone"
        v-model="phone"
        v-maska="'+380 ## ### ## ##'"
        type="tel"
        :placeholder="t('crm.clients.form.phonePlaceholder')"
        aria-required="true"
        :aria-invalid="!!phoneError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="phoneError" class="mt-1 text-xs text-destructive">{{ phoneError }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="client-email">{{ t('crm.clients.form.emailLabel') }}</label>
      <input
        id="client-email"
        v-model="email"
        type="email"
        :placeholder="t('crm.clients.form.emailPlaceholder')"
        :aria-invalid="!!emailError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="emailError" class="mt-1 text-xs text-destructive">{{ emailError }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="client-social-media">{{ t('crm.clients.form.socialMediaLabel') }}</label>
      <input
        id="client-social-media"
        v-model="socialMedia"
        type="text"
        :placeholder="t('crm.clients.form.socialMediaPlaceholder')"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground" for="client-lead-source">{{ t('crm.clients.form.leadSourceLabel') }}</label>
      <select
        id="client-lead-source"
        v-model="leadSource"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">{{ t('crm.clients.form.leadSourceNotSpecified') }}</option>
        <option v-for="leadSourceOption in CLIENT_LEAD_SOURCES" :key="leadSourceOption" :value="leadSourceOption">
          {{ t(getLeadSourceLabelKey(leadSourceOption)) }}
        </option>
      </select>
    </div>

    <div v-if="showListingSelector">
      <label class="block text-sm font-medium text-foreground" for="client-listing">{{ t('crm.clients.form.listingLabel') }} <RequiredMark /></label>
      <select
        id="client-listing"
        v-model="listingId"
        aria-required="true"
        :aria-invalid="!!listingIdError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">—</option>
        <option v-for="listing in availableListings" :key="listing.id" :value="listing.id">
          {{ listing.brand }} {{ listing.model }}, {{ listing.year }}
        </option>
      </select>
      <p v-if="listingIdError" class="mt-1 text-xs text-destructive">{{ listingIdError }}</p>
    </div>

    <div v-if="showEmployeeField">
      <label class="block text-sm font-medium text-foreground" for="client-employee">{{ t('crm.clients.form.employeeLabel') }}</label>
      <select
        id="client-employee"
        v-model="employeeId"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">{{ t('crm.clients.form.employeeNotAssigned') }}</option>
        <option v-for="employee in assignableEmployees" :key="employee.id" :value="employee.id">
          {{ getEmployeeDisplayName(employee, employee.email) }}{{ employee.is_active ? '' : ` (${t('crm.employees.inactiveStatus')})` }}
        </option>
      </select>
    </div>

    <div v-if="showNotesField">
      <label class="block text-sm font-medium text-foreground" for="client-notes">{{ t('crm.clients.form.notesLabel') }}</label>
      <textarea
        id="client-notes"
        v-model="notes"
        rows="4"
        :placeholder="t('crm.clients.form.notesPlaceholder')"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      />
    </div>

    <div
      v-if="clientStore.error"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ clientStore.error }}</span>
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
        :disabled="clientStore.isLoading || !meta.valid"
        class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ clientStore.isLoading ? submittingLabel : submitLabel }}
      </button>
    </div>
  </form>
</template>
