<script setup lang="ts">
import {
  ArrowUpTrayIcon,
  ClipboardIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
  TruckIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { Listing } from '~/types/listings'
import type { ListingPhoto } from '~/types/listingPhotos'

definePageMeta({ layout: 'business', middleware: ['auth', 'business'] })

const { t, n } = useI18n()
const authStore = useAuthStore()
const listingStore = useListingStore()
const telegramIntegrationStore = useTelegramIntegrationStore()

await Promise.all([listingStore.fetchListings(), telegramIntegrationStore.fetchStatus()])

// Only the owner can connect a Telegram channel (Settings' Telegram section
// is owner-only) — an employee has no way to act on the "go connect it"
// call to action, so they get a different not-connected message with no
// link, instead of a button that would lead nowhere useful for them.
const { isCompanyAdmin } = useUserRole()

interface ComposerPhoto {
  id: string
  previewUrl: string
  file: File
}

const postText = ref('')
const photos = ref<ComposerPhoto[]>([])
const selectedListing = ref<Listing | null>(null)

const isPickerOpen = ref(false)
const isConfirmOpen = ref(false)
const pendingListing = ref<Listing | null>(null)
const pendingClear = ref(false)

const copyFeedback = ref(false)

const hasUnsavedContent = computed<boolean>(() => postText.value.trim() !== '' || photos.value.length > 0)

function revokeAllPhotoUrls(): void {
  for (const photo of photos.value) {
    URL.revokeObjectURL(photo.previewUrl)
  }
}

function resetComposer(): void {
  revokeAllPhotoUrls()
  postText.value = ''
  photos.value = []
  selectedListing.value = null
}

const { apiGet, apiGetBlob } = useApi()

const isLoadingListingPhotos = ref(false)

async function applyListing(listing: Listing): Promise<void> {
  revokeAllPhotoUrls()
  photos.value = []
  selectedListing.value = listing
  postText.value = generateListingMarketingPost(listing, authStore.user?.company?.business_phone, t, (value) => n(value, 'currency'))

  isLoadingListingPhotos.value = true
  try {
    const listingPhotos = await apiGet<ListingPhoto[]>(`/listings/${listing.id}/photos`)
    for (const listingPhoto of listingPhotos) {
      const imageBlob = await apiGetBlob(`/listings/${listing.id}/photos/${listingPhoto.id}/file`)
      photos.value.push({
        id: `listing-photo-${listingPhoto.id}`,
        previewUrl: URL.createObjectURL(imageBlob),
        file: new File([imageBlob], `photo-${listingPhoto.id}.webp`, { type: 'image/webp' }),
      })
    }
  } catch {
    // photo autofill is a convenience — an empty gallery just means the user
    // adds photos manually, same as for a manually-composed post
  } finally {
    isLoadingListingPhotos.value = false
  }
}

function handleManualClick(): void {
  if (hasUnsavedContent.value) {
    pendingClear.value = true
    isConfirmOpen.value = true
    return
  }
  resetComposer()
}

function handlePickListingClick(): void {
  isPickerOpen.value = true
}

function handleListingSelected(listing: Listing): void {
  isPickerOpen.value = false

  if (hasUnsavedContent.value) {
    pendingListing.value = listing
    isConfirmOpen.value = true
    return
  }

  void applyListing(listing)
}

function handleConfirmAccept(): void {
  if (pendingListing.value) {
    void applyListing(pendingListing.value)
  } else if (pendingClear.value) {
    resetComposer()
  }
  pendingListing.value = null
  pendingClear.value = false
  isConfirmOpen.value = false
}

function handleConfirmCancel(): void {
  pendingListing.value = null
  pendingClear.value = false
  isConfirmOpen.value = false
}

function handleFileInputChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files) {
    return
  }

  for (const file of Array.from(files)) {
    photos.value.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      previewUrl: URL.createObjectURL(file),
      file,
    })
  }

  input.value = ''
}

function removePhoto(photoId: string): void {
  const photo = photos.value.find((existingPhoto) => existingPhoto.id === photoId)
  if (photo) {
    URL.revokeObjectURL(photo.previewUrl)
  }
  photos.value = photos.value.filter((existingPhoto) => existingPhoto.id !== photoId)
}

async function copyTextToClipboard(): Promise<void> {
  await navigator.clipboard.writeText(postText.value)
  copyFeedback.value = true
  setTimeout(() => { copyFeedback.value = false }, 2000)
}

const isPublishing = ref(false)
const publishError = ref('')
const publishSuccess = ref(false)

async function publishToTelegram(): Promise<void> {
  publishError.value = ''
  publishSuccess.value = false
  isPublishing.value = true

  try {
    await telegramIntegrationStore.publish(postText.value)
    publishSuccess.value = true
    setTimeout(() => { publishSuccess.value = false }, 4000)
  } catch (error) {
    publishError.value = (error as ApiError).message
  } finally {
    isPublishing.value = false
  }
}

onBeforeUnmount(() => {
  revokeAllPhotoUrls()
})
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <h1 class="text-xl font-semibold text-foreground">{{ t('crm.composer.title') }}</h1>

    <!-- TelegramNotConnectedBanner -->
    <div
      v-if="!telegramIntegrationStore.isConnected"
      class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-muted/50 p-3 text-sm text-muted-foreground"
    >
      <span>{{ isCompanyAdmin ? t('crm.composer.notConnectedBanner') : t('crm.composer.notConnectedBannerEmployee') }}</span>
      <NuxtLink
        v-if="isCompanyAdmin"
        to="/settings#telegram-section"
        class="whitespace-nowrap rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
      >
        {{ t('crm.composer.goToSettingsLink') }}
      </NuxtLink>
    </div>

    <!-- SourceToggle -->
    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        @click="handleManualClick"
      >
        <DocumentTextIcon class="size-4" />
        {{ t('crm.composer.manualButton') }}
      </button>
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        @click="handlePickListingClick"
      >
        <TruckIcon class="size-4" />
        {{ t('crm.composer.pickListingButton') }}
      </button>
    </div>

    <!-- SelectedListingChip -->
    <div v-if="selectedListing" class="flex items-center gap-2 rounded-md bg-primary/10 px-3 py-2 text-sm text-primary">
      <TruckIcon class="size-4 shrink-0" />
      <span>{{ t('crm.composer.sourceLabel') }}: {{ selectedListing.brand }} {{ selectedListing.model }}, {{ selectedListing.year }}</span>
    </div>

    <!-- TextSection -->
    <div>
      <label class="block text-sm font-medium text-foreground" for="composer-text">{{ t('crm.composer.textLabel') }}</label>
      <textarea
        id="composer-text"
        v-model="postText"
        rows="12"
        :placeholder="t('crm.composer.textPlaceholder')"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      />
    </div>

    <!-- PhotosSection -->
    <div>
      <label class="block text-sm font-medium text-foreground">{{ t('crm.composer.photosLabel') }}</label>

      <div class="mt-1.5 flex flex-wrap gap-3">
        <div v-for="photo in photos" :key="photo.id" class="group relative size-24 overflow-hidden rounded-md border border-border">
          <img :src="photo.previewUrl" class="size-full object-cover" :alt="t('crm.composer.photosLabel')">
          <button
            type="button"
            class="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
            :aria-label="t('common.buttons.delete')"
            @click="removePhoto(photo.id)"
          >
            <TrashIcon class="size-3.5" />
          </button>
        </div>

        <label class="flex size-24 cursor-pointer flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border-strong text-muted-foreground transition-colors hover:border-primary hover:text-primary">
          <ArrowUpTrayIcon class="size-5" />
          <span class="text-xs">{{ t('crm.composer.addPhotoButton') }}</span>
          <input type="file" accept="image/*" multiple class="hidden" @change="handleFileInputChange">
        </label>
      </div>

      <p v-if="isLoadingListingPhotos" class="mt-2 text-xs text-muted-foreground">
        {{ t('crm.composer.loadingListingPhotos') }}
      </p>
      <p v-else-if="selectedListing && photos.length === 0" class="mt-2 text-xs text-muted-foreground">
        {{ t('crm.composer.noListingPhotos') }}
      </p>
    </div>

    <!-- Actions -->
    <div class="space-y-3 border-t border-border pt-4">
      <div class="flex flex-wrap items-center gap-3">
        <button
          type="button"
          :disabled="!postText.trim()"
          class="flex items-center gap-1.5 rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
          @click="copyTextToClipboard"
        >
          <ClipboardIcon class="size-4" />
          {{ copyFeedback ? t('crm.composer.copiedFeedback') : t('crm.composer.copyButton') }}
        </button>

        <button
          v-if="telegramIntegrationStore.isConnected"
          type="button"
          :disabled="!postText.trim() || isPublishing"
          class="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          @click="publishToTelegram"
        >
          <PaperAirplaneIcon class="size-4" />
          {{ isPublishing ? t('crm.composer.sendingButton') : t('crm.composer.sendButton') }}
        </button>

        <p v-if="!telegramIntegrationStore.isConnected" class="text-xs text-muted-foreground">{{ t('crm.composer.sendNotice') }}</p>
      </div>

      <p v-if="telegramIntegrationStore.isConnected && photos.length > 0" class="text-xs text-muted-foreground">
        {{ t('crm.composer.photosNotSentHint') }}
      </p>

      <!-- PublishSuccessAlert -->
      <div
        v-if="publishSuccess"
        class="flex items-start gap-2 rounded-md border border-success/20 bg-success/10 p-3 text-sm text-success"
        role="status"
      >
        <PaperAirplaneIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ t('crm.composer.publishSuccessMessage') }}</span>
      </div>

      <!-- PublishErrorAlert -->
      <div
        v-if="publishError"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ publishError }}</span>
      </div>
    </div>

    <ListingPickerModal
      v-if="isPickerOpen"
      @select="handleListingSelected"
      @close="isPickerOpen = false"
    />

    <ConfirmDialog
      v-if="isConfirmOpen"
      :title="t('crm.composer.confirmTitle')"
      :message="pendingListing ? t('crm.composer.confirmReplaceMessage') : t('crm.composer.confirmClearMessage')"
      :confirm-label="t('common.buttons.continue')"
      @confirm="handleConfirmAccept"
      @cancel="handleConfirmCancel"
    />
  </div>
</template>
