<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { vMaska } from 'maska/vue'
import { useForm, useField } from 'vee-validate'
import type { Listing, ListingCondition, ListingFormInput, ListingStatus } from '~/types/listings'
import { CLIENT_LEAD_SOURCES, type ClientLeadSource, getLeadSourceLabelKey } from '~/utils/clientOptions'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'
import type { ListingFuelType } from '~/utils/listingOptions'

const props = defineProps<{
  initialListing?: Listing
  submitLabel: string
  submittingLabel: string
  showCancelButton?: boolean
  cancelLabel?: string
}>()

const emit = defineEmits<{ submit: [values: ListingFormInput, photoFiles: File[]], cancel: [] }>()

const { t, n } = useI18n()
const validators = createValidators(t)

const listingStore = useListingStore()
const { isCompanyAdmin } = useUserRole()

const today = new Date().toISOString().slice(0, 10)

const { meta, handleSubmit } = useForm()

// Seller fields only apply when creating a new listing — an existing
// listing's seller is a separate, already-created Client edited via the
// Clients board, not through this form. The validators are no-ops in edit
// mode so the (hidden) fields never block saving an existing listing.
const isCreateMode = computed<boolean>(() => !props.initialListing)

const { value: sellerName, errorMessage: sellerNameError } = useField<string>(
  'seller_name',
  (value: string) => isCreateMode.value ? validators.minLength(2)(value) : true,
  { initialValue: '' }
)
const { value: sellerPhone, errorMessage: sellerPhoneError } = useField<string>(
  'seller_phone',
  (value: string) => isCreateMode.value ? validators.ukrainianPhone(value) : true,
  { initialValue: '' }
)
const { value: sellerEmail, errorMessage: sellerEmailError } = useField<string>(
  'seller_email',
  (value: string) => isCreateMode.value ? validators.optionalEmail(value) : true,
  { initialValue: '' }
)
const { value: sellerSocialMedia } = useField<string>('seller_social_media', undefined, { initialValue: '' })
const { value: sellerLeadSource } = useField<ClientLeadSource | ''>('seller_lead_source', undefined, { initialValue: '' })
const { value: sellerEmployeeId } = useField<number | ''>('employee_id', undefined, { initialValue: '' })

const employeeStore = useEmployeeStore()
const activeEmployees = computed(() => employeeStore.employees.filter((employee) => employee.is_active))

const { value: brand, errorMessage: brandError } = useField<string>('brand', validators.required, { initialValue: props.initialListing?.brand ?? '' })
const { value: model, errorMessage: modelError } = useField<string>('model', validators.required, { initialValue: props.initialListing?.model ?? '' })
const { value: year, errorMessage: yearError } = useField<string>('year', validators.numericString, { initialValue: props.initialListing?.year ?? '' })
const { value: mileage, errorMessage: mileageError } = useField<string>('mileage', validators.numericString, { initialValue: props.initialListing?.mileage ?? '' })
const { value: vin } = useField<string>('vin', undefined, { initialValue: props.initialListing?.vin ?? '' })

const initialBodyType = props.initialListing?.body_type ?? ''
const bodyTypeSelectValue = ref<string>(initialBodyType && !isKnownBodyType(initialBodyType) ? OTHER_OPTION_VALUE : initialBodyType)
const bodyTypeManualValue = ref<string>(initialBodyType && !isKnownBodyType(initialBodyType) ? initialBodyType : '')
const { value: bodyType, errorMessage: bodyTypeError } = useField<string>('body_type', validators.required, { initialValue: initialBodyType })
watch([bodyTypeSelectValue, bodyTypeManualValue], () => {
  bodyType.value = bodyTypeSelectValue.value === OTHER_OPTION_VALUE ? bodyTypeManualValue.value : bodyTypeSelectValue.value
})

const initialTransmission = props.initialListing?.transmission ?? ''
const transmissionSelectValue = ref<string>(initialTransmission && !isKnownTransmission(initialTransmission) ? OTHER_OPTION_VALUE : initialTransmission)
const transmissionManualValue = ref<string>(initialTransmission && !isKnownTransmission(initialTransmission) ? initialTransmission : '')
const { value: transmission, errorMessage: transmissionError } = useField<string>('transmission', validators.required, { initialValue: initialTransmission })
watch([transmissionSelectValue, transmissionManualValue], () => {
  transmission.value = transmissionSelectValue.value === OTHER_OPTION_VALUE ? transmissionManualValue.value : transmissionSelectValue.value
})

const { value: engine, errorMessage: engineError } = useField<string>('engine', validators.required, { initialValue: props.initialListing?.engine ?? '' })
const { value: fuelType, errorMessage: fuelTypeError } = useField<ListingFuelType>('fuel_type', validators.required, { initialValue: props.initialListing?.fuel_type ?? 'petrol' })
const { value: color, errorMessage: colorError } = useField<string>('color', validators.required, { initialValue: props.initialListing?.color ?? '' })

const { value: condition, errorMessage: conditionError } = useField<ListingCondition>('condition', validators.required, { initialValue: props.initialListing?.condition ?? 'used' })
const { value: conditionDescription } = useField<string>('condition_description', undefined, { initialValue: props.initialListing?.condition_description ?? '' })
const { value: trimLevel } = useField<string>('trim_level', undefined, { initialValue: props.initialListing?.trim_level ?? '' })

const { value: purchasePrice, errorMessage: purchasePriceError } = useField<number | ''>('purchase_price', validators.positiveNumber, { initialValue: props.initialListing?.purchase_price ?? '' })
const { value: additionalExpenses, errorMessage: additionalExpensesError } = useField<number | ''>('additional_expenses', validators.optionalNonNegativeNumber, { initialValue: props.initialListing?.additional_expenses ?? 0 })
const { value: salePrice, errorMessage: salePriceError } = useField<number | ''>('sale_price', validators.positiveNumber, { initialValue: props.initialListing?.sale_price ?? '' })

function validateDiscountAmount(value: number | ''): true | string {
  if (value === '' || value === undefined || value === null) {
    return true
  }
  if (Number(value) < 0) {
    return t('validation.nonNegativeNumber')
  }
  const currentSalePrice = salePrice.value === '' ? 0 : Number(salePrice.value)
  if (Number(value) > currentSalePrice) {
    return t('listingForm.discountExceedsSalePrice')
  }
  return true
}

const { value: discountAmount, errorMessage: discountAmountError, validate: revalidateDiscountAmount } = useField<number | ''>('discount_amount', validateDiscountAmount, { initialValue: props.initialListing?.discount_amount ?? '' })

watch(salePrice, () => {
  revalidateDiscountAmount()
})

const { value: dateAdded } = useField<string>('date_added', undefined, { initialValue: props.initialListing?.date_added ?? today })
const { value: deadlineDate } = useField<string>('deadline_date', undefined, { initialValue: props.initialListing?.deadline_date ?? '' })

const { value: status } = useField<ListingStatus>('status', validators.required, { initialValue: props.initialListing?.status ?? 'draft' })

// Photos picked before the listing exists — held here as plain File objects
// and only actually uploaded (via POST /listings/{id}/photos) once the
// create request below succeeds and a real listing id exists.
const stagedPhotoFiles = ref<File[]>([])

// Same lock as "sold": on_service is only ever reachable through the
// dedicated "На СТО" modal (which requires a mandatory start date) and only
// ever left through "Повернути в роботу" on the СТО page — never through
// this plain status dropdown. "reserved" gets the same treatment for
// *entering* it — only reachable via the dedicated "Забронювати" modal
// (which requires picking a buyer) — but *leaving* reserved for something
// else is deliberately left reachable through this plain dropdown, same as
// it always was; no new behavior invented for that direction.
const availableStatusOptions = computed<ListingStatus[]>(() => {
  if (props.initialListing?.status === 'sold') {
    return ['sold']
  }
  if (props.initialListing?.status === 'on_service') {
    return ['on_service']
  }
  if (props.initialListing?.status === 'reserved') {
    return ['draft', 'active', 'reserved', 'removed']
  }
  return ['draft', 'active', 'removed']
})
const isStatusLocked = computed<boolean>(() =>
  props.initialListing?.status === 'sold' || props.initialListing?.status === 'on_service'
)

const totalCostPreview = computed<number>(() =>
  calculateTotalCost(
    purchasePrice.value === '' ? 0 : Number(purchasePrice.value),
    additionalExpenses.value === '' ? 0 : Number(additionalExpenses.value)
  )
)
const finalPricePreview = computed<number>(() =>
  calculateFinalPrice(
    salePrice.value === '' ? 0 : Number(salePrice.value),
    discountAmount.value === '' ? 0 : Number(discountAmount.value)
  )
)
const netProfitPreview = computed<number>(() => calculateNetProfit(finalPricePreview.value, totalCostPreview.value))

const discountedPriceDisplay = computed<number>(() => {
  const discountValue = discountAmount.value === '' ? 0 : Number(discountAmount.value)
  return discountValue > 0 ? finalPricePreview.value : 0
})

const submitForm = handleSubmit(() => {
  emit('submit', {
    brand: brand.value,
    model: model.value,
    year: year.value,
    mileage: mileage.value,
    vin: vin.value || undefined,
    body_type: bodyType.value,
    transmission: transmission.value,
    engine: engine.value,
    fuel_type: fuelType.value,
    color: color.value,
    condition: condition.value,
    condition_description: conditionDescription.value || undefined,
    trim_level: trimLevel.value || undefined,
    purchase_price: Number(purchasePrice.value),
    additional_expenses: additionalExpenses.value === '' ? 0 : Number(additionalExpenses.value),
    sale_price: Number(salePrice.value),
    discount_amount: discountAmount.value === '' ? undefined : Number(discountAmount.value),
    date_added: dateAdded.value || undefined,
    deadline_date: deadlineDate.value || undefined,
    status: status.value,
    ...(isCreateMode.value ? {
      seller_name: sellerName.value,
      seller_phone: sellerPhone.value,
      seller_email: sellerEmail.value || undefined,
      seller_social_media: sellerSocialMedia.value || undefined,
      seller_lead_source: sellerLeadSource.value || undefined,
      employee_id: sellerEmployeeId.value === '' ? null : Number(sellerEmployeeId.value),
    } : {}),
  }, stagedPhotoFiles.value)
})

// Lets an external trigger (the page header's "Змінити"/"Зберегти" toggle
// button) invoke the exact same validate-then-submit path as the form's own
// submit button, instead of duplicating the submit logic.
defineExpose({ requestSubmit: submitForm })
</script>

<template>
  <form class="space-y-6" @submit.prevent="submitForm">
    <!-- SellerSection -->
    <section v-if="isCreateMode" class="space-y-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.sellerSection') }}</h2>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-seller-name">{{ t('listingForm.sellerNameLabel') }} <RequiredMark /></label>
          <input
            id="listing-seller-name"
            v-model="sellerName"
            type="text"
            :placeholder="t('listingForm.sellerNamePlaceholder')"
            aria-required="true"
            :aria-invalid="!!sellerNameError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="sellerNameError" class="mt-1 text-xs text-destructive">{{ sellerNameError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-seller-phone">{{ t('listingForm.sellerPhoneLabel') }} <RequiredMark /></label>
          <input
            id="listing-seller-phone"
            v-model="sellerPhone"
            v-maska="'+380 ## ### ## ##'"
            type="tel"
            :placeholder="t('listingForm.sellerPhonePlaceholder')"
            aria-required="true"
            :aria-invalid="!!sellerPhoneError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="sellerPhoneError" class="mt-1 text-xs text-destructive">{{ sellerPhoneError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-seller-email">{{ t('listingForm.sellerEmailLabel') }}</label>
          <input
            id="listing-seller-email"
            v-model="sellerEmail"
            type="email"
            :placeholder="t('listingForm.sellerEmailPlaceholder')"
            :aria-invalid="!!sellerEmailError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="sellerEmailError" class="mt-1 text-xs text-destructive">{{ sellerEmailError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-seller-social-media">{{ t('listingForm.sellerSocialMediaLabel') }}</label>
          <input
            id="listing-seller-social-media"
            v-model="sellerSocialMedia"
            type="text"
            :placeholder="t('listingForm.sellerSocialMediaPlaceholder')"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-seller-lead-source">{{ t('crm.clients.form.leadSourceLabel') }}</label>
          <select
            id="listing-seller-lead-source"
            v-model="sellerLeadSource"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">{{ t('crm.clients.form.leadSourceNotSpecified') }}</option>
            <option v-for="leadSourceOption in CLIENT_LEAD_SOURCES" :key="leadSourceOption" :value="leadSourceOption">
              {{ t(getLeadSourceLabelKey(leadSourceOption)) }}
            </option>
          </select>
        </div>

        <div v-if="isCompanyAdmin">
          <label class="block text-sm font-medium text-foreground" for="listing-seller-employee">{{ t('listingForm.sellerEmployeeLabel') }}</label>
          <select
            id="listing-seller-employee"
            v-model="sellerEmployeeId"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">{{ t('crm.clients.form.employeeNotAssigned') }}</option>
            <option v-for="employee in activeEmployees" :key="employee.id" :value="employee.id">
              {{ getEmployeeDisplayName(employee, employee.email) }}
            </option>
          </select>
        </div>
      </div>
    </section>

    <!-- TechnicalSpecsSection -->
    <section :class="isCreateMode ? 'space-y-4 border-t border-border pt-4' : 'space-y-4'">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.technicalSection') }}</h2>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-brand">{{ t('listingForm.brandLabel') }} <RequiredMark /></label>
          <input id="listing-brand" v-model="brand" type="text" aria-required="true" :aria-invalid="!!brandError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="brandError" class="mt-1 text-xs text-destructive">{{ brandError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-model">{{ t('listingForm.modelLabel') }} <RequiredMark /></label>
          <input id="listing-model" v-model="model" type="text" aria-required="true" :aria-invalid="!!modelError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="modelError" class="mt-1 text-xs text-destructive">{{ modelError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-year">{{ t('listingForm.yearLabel') }} <RequiredMark /></label>
          <input id="listing-year" v-model="year" type="text" inputmode="numeric" aria-required="true" :aria-invalid="!!yearError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="yearError" class="mt-1 text-xs text-destructive">{{ yearError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-mileage">{{ t('listingForm.mileageLabel') }} <RequiredMark /></label>
          <input id="listing-mileage" v-model="mileage" type="text" inputmode="numeric" aria-required="true" :aria-invalid="!!mileageError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="mileageError" class="mt-1 text-xs text-destructive">{{ mileageError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-vin">{{ t('listingForm.vinLabel') }}</label>
          <input id="listing-vin" v-model="vin" type="text" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-body-type">{{ t('listingForm.bodyTypeLabel') }} <RequiredMark /></label>
          <select id="listing-body-type" v-model="bodyTypeSelectValue" aria-required="true" :aria-invalid="!!bodyTypeError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
            <option value="">—</option>
            <option v-for="bodyTypeOption in LISTING_BODY_TYPES" :key="bodyTypeOption" :value="bodyTypeOption">{{ t(getBodyTypeLabelKey(bodyTypeOption)!) }}</option>
            <option :value="OTHER_OPTION_VALUE">{{ t('listingForm.otherOption') }}</option>
          </select>
          <input
            v-if="bodyTypeSelectValue === OTHER_OPTION_VALUE"
            v-model="bodyTypeManualValue"
            type="text"
            :placeholder="t('listingForm.bodyTypeOtherPlaceholder')"
            class="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="bodyTypeError" class="mt-1 text-xs text-destructive">{{ bodyTypeError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-transmission">{{ t('listingForm.transmissionLabel') }} <RequiredMark /></label>
          <select id="listing-transmission" v-model="transmissionSelectValue" aria-required="true" :aria-invalid="!!transmissionError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
            <option value="">—</option>
            <option v-for="transmissionOption in LISTING_TRANSMISSIONS" :key="transmissionOption" :value="transmissionOption">{{ t(getTransmissionLabelKey(transmissionOption)!) }}</option>
            <option :value="OTHER_OPTION_VALUE">{{ t('listingForm.otherOption') }}</option>
          </select>
          <input
            v-if="transmissionSelectValue === OTHER_OPTION_VALUE"
            v-model="transmissionManualValue"
            type="text"
            :placeholder="t('listingForm.transmissionOtherPlaceholder')"
            class="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="transmissionError" class="mt-1 text-xs text-destructive">{{ transmissionError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-engine">{{ t('listingForm.engineLabel') }} <RequiredMark /></label>
          <input id="listing-engine" v-model="engine" type="text" aria-required="true" :aria-invalid="!!engineError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="engineError" class="mt-1 text-xs text-destructive">{{ engineError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-fuel-type">{{ t('carForm.fuelTypeLabel') }} <RequiredMark /></label>
          <select id="listing-fuel-type" v-model="fuelType" aria-required="true" :aria-invalid="!!fuelTypeError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
            <option v-for="fuelTypeOption in LISTING_FUEL_TYPES" :key="fuelTypeOption" :value="fuelTypeOption">{{ t(getListingFuelTypeLabelKey(fuelTypeOption)) }}</option>
          </select>
          <p v-if="fuelTypeError" class="mt-1 text-xs text-destructive">{{ fuelTypeError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-color">{{ t('listingForm.colorLabel') }} <RequiredMark /></label>
          <input id="listing-color" v-model="color" type="text" aria-required="true" :aria-invalid="!!colorError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="colorError" class="mt-1 text-xs text-destructive">{{ colorError }}</p>
        </div>
      </div>
    </section>

    <!-- ConditionSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.conditionSection') }}</h2>

      <div>
        <label class="block text-sm font-medium text-foreground" for="listing-condition">{{ t('listingForm.conditionLabel') }} <RequiredMark /></label>
        <select id="listing-condition" v-model="condition" aria-required="true" :aria-invalid="!!conditionError" class="mt-1.5 w-full max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <option value="new">{{ t('listingForm.conditionNew') }}</option>
          <option value="used">{{ t('listingForm.conditionUsed') }}</option>
        </select>
        <p v-if="conditionError" class="mt-1 text-xs text-destructive">{{ conditionError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="listing-trim-level">{{ t('listingForm.trimLevelLabel') }}</label>
        <textarea
          id="listing-trim-level"
          v-model="trimLevel"
          rows="3"
          :placeholder="t('listingForm.trimLevelPlaceholder')"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="listing-condition-description">{{ t('listingForm.conditionDescriptionLabel') }}</label>
        <textarea id="listing-condition-description" v-model="conditionDescription" rows="3" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary" />
      </div>

      <ListingPhotoGallery v-if="isCreateMode" v-model:staged-files="stagedPhotoFiles" staging-mode />
      <ListingPhotoGallery v-else :listing-id="initialListing!.id" is-edit-mode />
    </section>

    <!-- CommercialSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.commercialSection') }}</h2>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-purchase-price">{{ t('listingForm.purchasePriceLabel') }} <RequiredMark /></label>
          <input id="listing-purchase-price" v-model.number="purchasePrice" type="number" min="0" step="0.01" aria-required="true" :aria-invalid="!!purchasePriceError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="purchasePriceError" class="mt-1 text-xs text-destructive">{{ purchasePriceError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-additional-expenses">{{ t('listingForm.additionalExpensesLabel') }}</label>
          <input id="listing-additional-expenses" v-model.number="additionalExpenses" type="number" min="0" step="0.01" :aria-invalid="!!additionalExpensesError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="additionalExpensesError" class="mt-1 text-xs text-destructive">{{ additionalExpensesError }}</p>
        </div>

        <!-- TotalCostPreview -->
        <div class="rounded-md bg-muted px-3 py-2 sm:col-span-2">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.totalCostLabel') }}</p>
          <p class="mt-0.5 text-base font-semibold tabular-nums text-foreground">{{ n(totalCostPreview, 'currency') }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-sale-price">{{ t('listingForm.salePriceLabel') }} <RequiredMark /></label>
          <input id="listing-sale-price" v-model.number="salePrice" type="number" min="0" step="0.01" aria-required="true" :aria-invalid="!!salePriceError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="salePriceError" class="mt-1 text-xs text-destructive">{{ salePriceError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-discount-amount">{{ t('listingForm.discountAmountLabel') }}</label>
          <input id="listing-discount-amount" v-model.number="discountAmount" type="number" min="0" step="0.01" :aria-invalid="!!discountAmountError" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
          <p v-if="discountAmountError" class="mt-1 text-xs text-destructive">{{ discountAmountError }}</p>
        </div>

        <!-- FinalPricePreview -->
        <div class="rounded-md bg-muted px-3 py-2">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.finalPriceLabel') }}</p>
          <p class="mt-0.5 text-base font-semibold tabular-nums text-foreground">{{ n(discountedPriceDisplay, 'currency') }}</p>
        </div>

        <!-- NetProfitPreview -->
        <div class="rounded-md bg-primary/5 px-3 py-2">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.netProfitLabel') }}</p>
          <p
            class="mt-0.5 text-base font-semibold tabular-nums"
            :class="netProfitPreview >= 0 ? 'text-success' : 'text-destructive'"
          >
            {{ n(netProfitPreview, 'currency') }}
          </p>
        </div>
      </div>
    </section>

    <!-- TimelineSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.timelineSection') }}</h2>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-date-added">{{ t('listingForm.dateAddedLabel') }}</label>
          <input id="listing-date-added" v-model="dateAdded" type="date" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-deadline-date">{{ t('listingForm.deadlineDateLabel') }}</label>
          <input id="listing-deadline-date" v-model="deadlineDate" type="date" class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary">
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="listing-status">{{ t('listingForm.statusLabel') }} <RequiredMark /></label>
          <select id="listing-status" v-model="status" :disabled="isStatusLocked" aria-required="true" class="mt-1.5 w-full max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60">
            <option v-for="statusOption in availableStatusOptions" :key="statusOption" :value="statusOption">{{ t(`listingStatus.${statusOption}`) }}</option>
          </select>
        </div>
      </div>
    </section>

    <!-- ErrorAlert -->
    <div
      v-if="listingStore.error"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ listingStore.error }}</span>
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
        :disabled="listingStore.isLoading || !meta.valid"
        class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {{ listingStore.isLoading ? submittingLabel : submitLabel }}
      </button>
    </div>
  </form>
</template>
