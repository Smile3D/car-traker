<script setup lang="ts">
import type { ListingFormInput } from '~/types/listings'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t } = useI18n()
const router = useRouter()

const listingStore = useListingStore()
const clientStore = useClientStore()
const employeeStore = useEmployeeStore()
const listingPhotoStore = useListingPhotoStore()

// The responsible-employee select is owner/co-founder-only (employees always
// self-assign server-side), and GET /employees itself is an
// owner/co-founder-only endpoint — fetching it for a plain employee would
// just be a wasted 403.
const { isCompanyAdmin } = useUserRole()
if (isCompanyAdmin.value) {
  await employeeStore.fetchEmployees()
}

const isUploadingPhotos = ref(false)
const photoUploadTotal = ref(0)
const photoUploadCompleted = ref(0)

async function handleSubmit(values: ListingFormInput, photoFiles: File[]): Promise<void> {
  try {
    const createdListing = await listingStore.createListing(values)
    // POST /listings also creates the seller Client server-side; refetch the
    // full client list so it shows up on the Clients → Sellers board without
    // a separate creation flow.
    await clientStore.fetchClients()

    // The listing now exists — attach any photos staged before submit, one
    // request per file so "N з M" progress can be shown. A failed listing
    // creation above must never reach here (nothing to attach yet), but a
    // failure here must never undo the listing itself: it already exists
    // with correct data, so we still navigate to it and just warn about
    // whichever photos didn't make it.
    let failedPhotoCount = 0
    if (photoFiles.length > 0) {
      isUploadingPhotos.value = true
      photoUploadTotal.value = photoFiles.length
      photoUploadCompleted.value = 0

      for (const file of photoFiles) {
        try {
          const result = await listingPhotoStore.uploadPhotos(createdListing.id, [file])
          failedPhotoCount += result.errors.length
        } catch {
          failedPhotoCount += 1
        } finally {
          photoUploadCompleted.value += 1
        }
      }
    }

    router.push({
      path: `/crm/inventory/${createdListing.id}`,
      query: failedPhotoCount > 0 ? { photosFailed: String(failedPhotoCount) } : undefined,
    })
  } catch {
    // ошибка уже сохранена в listingStore.error и показана у формі
  } finally {
    isUploadingPhotos.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <h1 class="text-xl font-semibold text-foreground">{{ t('listingForm.addTitle') }}</h1>

    <div class="rounded-lg border border-border bg-surface p-5 shadow-card">
      <ListingForm
        :submit-label="t('common.buttons.add')"
        :submitting-label="t('common.buttons.adding')"
        @submit="handleSubmit"
      />
    </div>

    <!-- PhotoUploadProgress -->
    <div
      v-if="isUploadingPhotos"
      class="flex items-center gap-2 rounded-lg border border-border bg-surface p-4 text-sm text-foreground shadow-card"
    >
      <svg class="size-4 shrink-0 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z" />
      </svg>
      {{ t('listingForm.uploadingPhotosProgress', { completed: photoUploadCompleted, total: photoUploadTotal }) }}
    </div>
  </div>
</template>
