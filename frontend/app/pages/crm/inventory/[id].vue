<script setup lang="ts">
import { ArrowLeftIcon, BookmarkIcon, CheckIcon, ExclamationTriangleIcon, PencilSquareIcon, TagIcon, TrashIcon, WrenchScrewdriverIcon } from '@heroicons/vue/24/outline'
import type { ListingFormInput } from '~/types/listings'
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, d } = useI18n()
const route = useRoute()
const router = useRouter()

const authStore = useAuthStore()
const listingStore = useListingStore()
const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const employeeStore = useEmployeeStore()

const listingId = Number(route.params.id)
const notFound = ref(false)
const isEditMode = ref(false)
const isMarkSoldModalOpen = ref(false)
const isMarkOnServiceModalOpen = ref(false)
const isMarkReservedModalOpen = ref(false)
const isDeleteConfirmOpen = ref(false)
const showMovedToArchiveBanner = ref(false)
const showMovedToServiceBanner = ref(false)
const showReservedBanner = ref(false)

// Marking sold doesn't redirect (the user stays on this same detail page,
// which still works fine for a sold listing) — just a brief heads-up that
// it won't show up in Inventory's default view anymore.
function handleListingSold(): void {
  isMarkSoldModalOpen.value = false
  showMovedToArchiveBanner.value = true
  setTimeout(() => { showMovedToArchiveBanner.value = false }, 5000)
}

// Same idea as handleListingSold — stays on this page, just a brief
// heads-up that the lot moved off Inventory's default view onto СТО.
function handleListingMarkedOnService(): void {
  isMarkOnServiceModalOpen.value = false
  showMovedToServiceBanner.value = true
  setTimeout(() => { showMovedToServiceBanner.value = false }, 5000)
}

function handleListingReserved(): void {
  isMarkReservedModalOpen.value = false
  showReservedBanner.value = true
  setTimeout(() => { showReservedBanner.value = false }, 5000)
}

// Set by the "Додати лот" flow via a ?photosFailed= query param when the
// listing itself was created successfully but one or more staged photos
// failed to upload afterwards — stripped from the URL immediately so it
// doesn't reappear on refresh/back-navigation.
const failedPhotoUploadCount = ref<number | null>(null)
const photosFailedQueryValue = Array.isArray(route.query.photosFailed) ? route.query.photosFailed[0] : route.query.photosFailed
if (photosFailedQueryValue) {
  const parsedCount = Number(photosFailedQueryValue)
  if (Number.isFinite(parsedCount) && parsedCount > 0) {
    failedPhotoUploadCount.value = parsedCount
  }
  const { photosFailed: _removedPhotosFailed, ...remainingQuery } = route.query
  router.replace({ query: remainingQuery })
}

// undefined = the responsible employee wasn't touched during this edit
// session, so handleSubmit should leave the seller Client alone.
const pendingSellerEmployeeId = ref<number | null | undefined>(undefined)

// Same idea, fanned out over N buyers: only the buyer ids actually touched
// during this edit session end up here, keyed by client id.
const pendingBuyerEmployeeChanges = ref<Map<number, number | null>>(new Map())

function handleSellerEmployeeChange(employeeId: number | null): void {
  pendingSellerEmployeeId.value = employeeId
}

function handleBuyerEmployeeChange(buyerId: number, employeeId: number | null): void {
  pendingBuyerEmployeeChanges.value.set(buyerId, employeeId)
}

function handleEditClick(): void {
  pendingSellerEmployeeId.value = undefined
  pendingBuyerEmployeeChanges.value = new Map()
  isEditMode.value = true
}

// The header button is one control for two states: "Змінити" enters edit
// mode (unchanged); "Зберегти" triggers the exact same submit path as the
// form's own bottom button, via the ref exposed from ListingForm — no
// separate save logic here.
const listingFormRef = useTemplateRef('listingFormRef')

function handleHeaderActionClick(): void {
  if (isEditMode.value) {
    listingFormRef.value?.requestSubmit()
  } else {
    handleEditClick()
  }
}

function handleCancel(): void {
  pendingSellerEmployeeId.value = undefined
  pendingBuyerEmployeeChanges.value = new Map()
  isEditMode.value = false
}

const listing = computed(() => listingStore.listings.find((existingListing) => existingListing.id === listingId))

// Archived (sold/removed) lots are closed records — editing and single-lot
// deletion both go through the Archive's bulk-delete flow instead.
const isArchived = computed<boolean>(() => listing.value?.status === 'sold' || listing.value?.status === 'removed')

const { isEmployee, isCompanyAdmin } = useUserRole()

const responsibleEmployeeId = computed<number | null>(() => listing.value?.seller?.employee_id ?? null)

// Mirrors the backend rule in listing_authorization.py: unassigned (null) or
// self-assigned stays actionable; assigned to someone else is locked.
const isForeignListing = computed<boolean>(() =>
  isEmployee.value && responsibleEmployeeId.value !== null && responsibleEmployeeId.value !== authStore.user?.id
)

const responsibleEmployeeName = computed<string | undefined>(() =>
  getEmployeeDisplayName(listing.value?.seller?.employee ?? null, listing.value?.seller?.employee?.email)
)

if (Number.isNaN(listingId)) {
  notFound.value = true
} else if (!listing.value) {
  try {
    await listingStore.fetchListingById(listingId)
  } catch {
    notFound.value = true
  }
}

// Needed for the "Продавець" section: the seller Client, its stage badge,
// and the responsible-employee select. GET /employees is owner/co-founder-only
// — an employee viewer still sees the current assignee via ClientOut.employee,
// it just can't reassign to a different employee, so skip the fetch for them.
const fetchTasks = [clientStore.fetchClients(), clientStageStore.fetchStages()]
if (isCompanyAdmin.value) {
  fetchTasks.push(employeeStore.fetchEmployees())
}
await Promise.all(fetchTasks)

async function handleSubmit(values: ListingFormInput): Promise<void> {
  if (!listing.value) {
    return
  }

  try {
    await listingStore.updateListing(listing.value.id, values)

    // The responsible employee lives on the seller Client, not the Listing —
    // apply it as a second request so both changes land from one "Зберегти"
    // click. Left alone (undefined) if the select was never touched.
    if (pendingSellerEmployeeId.value !== undefined) {
      const sellerClient = clientStore.clients.find(
        (client) => client.listing_id === listing.value!.id && client.client_type === 'seller'
      )
      if (sellerClient) {
        await clientStore.updateClient(sellerClient.id, { employee_id: pendingSellerEmployeeId.value })
      }
    }

    for (const [buyerId, employeeId] of pendingBuyerEmployeeChanges.value) {
      await clientStore.updateClient(buyerId, { employee_id: employeeId })
    }

    pendingSellerEmployeeId.value = undefined
    pendingBuyerEmployeeChanges.value = new Map()
    isEditMode.value = false
  } catch {
    // ошибка уже сохранена в listingStore.error и показана в форме
  }
}

async function handleDeleteConfirm(reason: string | undefined): Promise<void> {
  if (!listing.value) {
    return
  }

  await listingStore.deleteListing(listing.value.id, reason)
  router.push('/crm/inventory')
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <NuxtLink to="/crm/inventory" class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeftIcon class="size-4" />
      {{ t('crm.inventory.title') }}
    </NuxtLink>

    <!-- ListingNotFound -->
    <div
      v-if="notFound"
      class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
    >
      <ExclamationTriangleIcon class="size-8 text-muted-foreground" />
      <p class="font-medium text-foreground">{{ t('listingDetails.notFound') }}</p>
    </div>

    <template v-else-if="listing">
      <!-- MovedToArchiveNotice -->
      <div
        v-if="showMovedToArchiveBanner"
        class="flex items-center gap-2 rounded-lg border border-success/20 bg-success/10 p-4 text-sm text-success"
        role="status"
      >
        <span>{{ t('listingDetails.movedToArchiveMessage') }}</span>
      </div>

      <!-- MovedToServiceNotice -->
      <div
        v-if="showMovedToServiceBanner"
        class="flex items-center gap-2 rounded-lg border border-success/20 bg-success/10 p-4 text-sm text-success"
        role="status"
      >
        <span>{{ t('listingDetails.movedToServiceMessage') }}</span>
      </div>

      <!-- ReservedNotice -->
      <div
        v-if="showReservedBanner"
        class="flex items-center gap-2 rounded-lg border border-success/20 bg-success/10 p-4 text-sm text-success"
        role="status"
      >
        <span>{{ t('listingDetails.movedToReservedMessage') }}</span>
      </div>

      <!-- PhotoUploadWarning -->
      <div
        v-if="failedPhotoUploadCount"
        class="flex items-start justify-between gap-2 rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
        role="alert"
      >
        <span>{{ t('listingDetails.photoUploadPartialFailure', { count: failedPhotoUploadCount }) }}</span>
        <button type="button" class="shrink-0 font-medium hover:underline" @click="failedPhotoUploadCount = null">
          {{ t('common.buttons.close') }}
        </button>
      </div>

      <!-- ListingDetailsHeader -->
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface p-5 shadow-card">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold text-foreground">{{ listing.brand }} {{ listing.model }}</h1>
            <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="getListingStatusBadgeClasses(listing.status)">
              {{ t(`listingStatus.${listing.status}`) }}
            </span>
          </div>
          <p v-if="listing.date_sold" class="mt-1 text-sm text-muted-foreground">
            {{ t('listingDetails.soldOn') }}: {{ d(new Date(listing.date_sold), 'short') }}
          </p>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            v-if="!isArchived && !isForeignListing"
            type="button"
            class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="isEditMode && listingStore.isLoading"
            @click="handleHeaderActionClick"
          >
            <CheckIcon v-if="isEditMode" class="size-4" />
            <PencilSquareIcon v-else class="size-4" />
            {{ isEditMode ? t('common.buttons.save') : t('common.buttons.edit') }}
          </button>
          <button
            v-if="listing.status !== 'sold' && !isForeignListing"
            type="button"
            class="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
            @click="isMarkSoldModalOpen = true"
          >
            <TagIcon class="size-4" />
            {{ t('listingDetails.markSold') }}
          </button>
          <button
            v-if="listing.status !== 'sold' && listing.status !== 'on_service' && !isForeignListing"
            type="button"
            class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            @click="isMarkOnServiceModalOpen = true"
          >
            <WrenchScrewdriverIcon class="size-4" />
            {{ t('listingDetails.markOnService') }}
          </button>
          <button
            v-if="listing.status !== 'sold' && listing.status !== 'on_service' && listing.status !== 'reserved' && !isForeignListing"
            type="button"
            class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            @click="isMarkReservedModalOpen = true"
          >
            <BookmarkIcon class="size-4" />
            {{ t('listingDetails.markReserved') }}
          </button>
          <button
            v-if="!isArchived && !isForeignListing"
            type="button"
            class="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
            @click="isDeleteConfirmOpen = true"
          >
            <TrashIcon class="size-4" />
            {{ t('common.buttons.delete') }}
          </button>
        </div>
      </div>

      <!-- ForeignListingNotice -->
      <div
        v-if="isForeignListing"
        class="flex items-center gap-2 rounded-lg border border-border-strong bg-muted/50 p-4 text-sm text-muted-foreground"
        role="status"
      >
        <span>
          {{ t('listingDetails.foreignListingNotice') }}<template v-if="responsibleEmployeeName"> ({{ responsibleEmployeeName }})</template>
        </span>
      </div>

      <ListingSellerSection
        :listing-id="listing.id"
        :is-edit-mode="isEditMode"
        :is-archived="isArchived"
        @employee-change="handleSellerEmployeeChange"
      />

      <ListingBuyersSection
        :listing-id="listing.id"
        :listing-status="listing.status"
        :is-edit-mode="isEditMode"
        :is-archived="isArchived"
        :is-foreign-listing="isForeignListing"
        @employee-change="handleBuyerEmployeeChange"
      />

      <div class="rounded-lg border border-border bg-surface p-5 shadow-card">
        <ListingDetailsReadOnly v-if="!isEditMode" :listing="listing" />
        <ListingForm
          v-else
          ref="listingFormRef"
          :initial-listing="listing"
          :submit-label="t('common.buttons.save')"
          :submitting-label="t('common.buttons.saving')"
          show-cancel-button
          :cancel-label="t('common.buttons.cancel')"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
      </div>

      <MarkSoldModal
        v-if="isMarkSoldModalOpen"
        :listing="listing"
        @close="isMarkSoldModalOpen = false"
        @sold="handleListingSold"
      />

      <MarkOnServiceModal
        v-if="isMarkOnServiceModalOpen"
        :listing="listing"
        @close="isMarkOnServiceModalOpen = false"
        @marked-on-service="handleListingMarkedOnService"
      />

      <MarkReservedModal
        v-if="isMarkReservedModalOpen"
        :listing="listing"
        @close="isMarkReservedModalOpen = false"
        @reserved="handleListingReserved"
      />

      <ListingDeleteConfirmModal
        v-if="isDeleteConfirmOpen"
        @confirm="handleDeleteConfirm"
        @cancel="isDeleteConfirmOpen = false"
      />
    </template>
  </div>
</template>
