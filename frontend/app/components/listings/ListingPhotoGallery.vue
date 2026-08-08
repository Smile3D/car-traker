<script setup lang="ts">
import { ArrowUpTrayIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import draggable from 'vuedraggable'
import type { ApiError } from '~/composables/useApi'
import type { ListingPhoto } from '~/types/listingPhotos'

const props = withDefaults(defineProps<{
  listingId?: number
  isEditMode?: boolean
  stagingMode?: boolean
}>(), {
  isEditMode: false,
  stagingMode: false,
})

// Staging mode (the "Додати лот" form, before the listing exists): staged
// files live in the parent's state and are just File objects — nothing is
// uploaded until the listing itself is created.
const stagedFiles = defineModel<File[]>('stagedFiles', { default: () => [] })

const { t } = useI18n()

const listingPhotoStore = useListingPhotoStore()

if (!props.stagingMode) {
  await listingPhotoStore.fetchPhotos(props.listingId!)
}

const MAX_PHOTOS = 15
const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
const ALLOWED_CONTENT_TYPES: ReadonlySet<string> = new Set(['image/jpeg', 'image/png', 'image/webp'])

// Decoupled from listingPhotoStore.photos on purpose (see BoardSettingsModal
// for the same pattern): vuedraggable mutates this array directly on every
// intermediate step of a drag, and a watcher reading the very same array it
// mutates would self-trigger and revert the reorder before @change ever
// sees it. Watching the store's (different) array and syncing one-way avoids
// that.
const orderedPhotos = reactive<ListingPhoto[]>([])

function syncOrderedPhotos(): void {
  const sortedPhotos = [...listingPhotoStore.photos].sort((a, b) => a.order - b.order)
  orderedPhotos.splice(0, Infinity, ...sortedPhotos)
}

if (!props.stagingMode) {
  watch(() => listingPhotoStore.photos, syncOrderedPhotos, { immediate: true, deep: true })
}

const isAtLimit = computed<boolean>(() =>
  props.stagingMode ? stagedFiles.value.length >= MAX_PHOTOS : orderedPhotos.length >= MAX_PHOTOS
)
const isDraggingOver = ref(false)
const isUploading = ref(false)
const uploadErrors = ref<string[]>([])

// One object URL per staged File, created lazily and memoized so the same
// File instance always resolves to the same preview — revoked explicitly on
// removal/unmount rather than left for garbage collection.
const previewUrlByFile = new Map<File, string>()

function getPreviewUrl(file: File): string {
  let previewUrl = previewUrlByFile.get(file)
  if (!previewUrl) {
    previewUrl = URL.createObjectURL(file)
    previewUrlByFile.set(file, previewUrl)
  }
  return previewUrl
}

function revokePreviewUrl(file: File): void {
  const previewUrl = previewUrlByFile.get(file)
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl)
    previewUrlByFile.delete(file)
  }
}

onUnmounted(() => {
  if (props.stagingMode) {
    for (const file of previewUrlByFile.keys()) {
      revokePreviewUrl(file)
    }
  }
})

function removeStagedFile(index: number): void {
  const [removedFile] = stagedFiles.value.splice(index, 1)
  if (removedFile) {
    revokePreviewUrl(removedFile)
  }
}

// Mirrors the backend's own per-file validation (upload_listing_photos) so
// the user finds out about limit/type/size problems immediately, without a
// round-trip — the real endpoint re-checks all of this anyway once the
// listing exists and these files are actually uploaded.
function stageFiles(files: File[]): void {
  const errors: string[] = []
  const acceptedFiles: File[] = []

  for (const file of files) {
    const displayName = file.name || 'photo'

    if (stagedFiles.value.length + acceptedFiles.length >= MAX_PHOTOS) {
      errors.push(t('listingPhotos.stagingLimitError', { name: displayName, max: MAX_PHOTOS }))
      continue
    }
    if (!ALLOWED_CONTENT_TYPES.has(file.type)) {
      errors.push(t('listingPhotos.stagingTypeError', { name: displayName }))
      continue
    }
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      errors.push(t('listingPhotos.stagingSizeError', { name: displayName }))
      continue
    }

    acceptedFiles.push(file)
  }

  if (acceptedFiles.length > 0) {
    stagedFiles.value = [...stagedFiles.value, ...acceptedFiles]
  }
  uploadErrors.value = errors
}

async function uploadFiles(files: File[]): Promise<void> {
  if (files.length === 0) {
    return
  }

  uploadErrors.value = []
  isUploading.value = true
  try {
    const result = await listingPhotoStore.uploadPhotos(props.listingId!, files)
    uploadErrors.value = result.errors
  } catch (e) {
    uploadErrors.value = [(e as ApiError).message]
  } finally {
    isUploading.value = false
  }
}

function handleDrop(dragEvent: DragEvent): void {
  isDraggingOver.value = false
  if (isAtLimit.value) {
    return
  }

  const files = dragEvent.dataTransfer?.files
  if (files && files.length > 0) {
    if (props.stagingMode) {
      stageFiles(Array.from(files))
    } else {
      void uploadFiles(Array.from(files))
    }
  }
}

function handleFileInputChange(changeEvent: Event): void {
  const input = changeEvent.target as HTMLInputElement
  const files = input.files
  if (files && files.length > 0) {
    if (props.stagingMode) {
      stageFiles(Array.from(files))
    } else {
      void uploadFiles(Array.from(files))
    }
  }
  input.value = ''
}

async function handleReorder(): Promise<void> {
  try {
    await listingPhotoStore.reorderPhotos(props.listingId!, orderedPhotos.map((photo) => photo.id))
  } catch {
    syncOrderedPhotos()
  }
}

const lightboxImageUrl = ref<string | null>(null)

function openLightbox(imageUrl: string): void {
  lightboxImageUrl.value = imageUrl
}

const photoPendingDeletion = ref<ListingPhoto | null>(null)

async function handleConfirmDelete(): Promise<void> {
  if (!photoPendingDeletion.value) {
    return
  }

  await listingPhotoStore.deletePhoto(props.listingId!, photoPendingDeletion.value.id)
  photoPendingDeletion.value = null
}
</script>

<template>
  <div>
    <p class="block text-sm font-medium text-foreground">{{ t('listingPhotos.title') }}</p>

    <!-- ReadOnlyEmptyState -->
    <p v-if="!isEditMode && !stagingMode && orderedPhotos.length === 0" class="mt-1.5 text-sm text-muted-foreground">
      {{ t('listingPhotos.emptyState') }}
    </p>

    <div v-else class="mt-1.5 flex flex-wrap gap-3">
      <!-- Read-only: plain thumbnails, no drag, no delete. -->
      <template v-if="!isEditMode && !stagingMode">
        <ListingPhotoThumbnail
          v-for="(photo, index) in orderedPhotos"
          :key="photo.id"
          :listing-id="listingId"
          :photo="photo"
          :is-cover="index === 0"
          @open="openLightbox"
        />
      </template>

      <!-- Staging: local File previews only, no backend calls until submit. -->
      <template v-else-if="stagingMode">
        <ListingPhotoThumbnail
          v-for="(file, index) in stagedFiles"
          :key="index"
          :preview-url="getPreviewUrl(file)"
          :is-cover="index === 0"
          is-edit-mode
          @open="openLightbox"
          @delete="removeStagedFile(index)"
        />
      </template>

      <!-- Edit mode: draggable to reorder, delete button per tile. -->
      <draggable
        v-else
        :list="orderedPhotos"
        item-key="id"
        class="contents"
        ghost-class="opacity-40"
        @change="handleReorder"
      >
        <template #item="{ element: photo, index }">
          <ListingPhotoThumbnail
            :listing-id="listingId"
            :photo="photo"
            :is-cover="index === 0"
            is-edit-mode
            @open="openLightbox"
            @delete="photoPendingDeletion = photo"
          />
        </template>
      </draggable>

      <!-- UploadTile: click or drag&drop, sized to match the thumbnails. -->
      <label
        v-if="(isEditMode || stagingMode) && !isAtLimit"
        for="listing-photo-upload"
        class="flex size-24 shrink-0 cursor-pointer flex-col items-center justify-center gap-1 rounded-md border border-dashed px-1 text-center transition-colors"
        :class="isDraggingOver ? 'border-primary bg-primary/5' : 'border-border-strong text-muted-foreground hover:border-primary hover:text-primary'"
        @dragover.prevent="isDraggingOver = true"
        @dragleave.prevent="isDraggingOver = false"
        @drop.prevent="handleDrop"
      >
        <ArrowUpTrayIcon class="size-5" />
        <span class="text-xs leading-tight">{{ isUploading ? t('listingPhotos.uploading') : t('listingPhotos.uploadHint') }}</span>
        <input
          id="listing-photo-upload"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          :disabled="isUploading"
          class="sr-only"
          @change="handleFileInputChange"
        >
      </label>

      <p v-if="(isEditMode || stagingMode) && isAtLimit" class="flex size-24 shrink-0 items-center justify-center rounded-md border border-dashed border-border-strong px-2 text-center text-xs text-muted-foreground">
        {{ t('listingPhotos.limitReached', { max: MAX_PHOTOS }) }}
      </p>
    </div>

    <!-- UploadErrors -->
    <div
      v-if="uploadErrors.length > 0"
      class="mt-2 space-y-1 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <p v-for="uploadError in uploadErrors" :key="uploadError" class="flex items-start gap-1.5">
        <ExclamationTriangleIcon class="mt-0.5 size-3.5 shrink-0" />
        <span>{{ uploadError }}</span>
      </p>
    </div>

    <ListingPhotoLightboxModal
      v-if="lightboxImageUrl"
      :image-url="lightboxImageUrl"
      @close="lightboxImageUrl = null"
    />

    <ConfirmDialog
      v-if="photoPendingDeletion"
      :title="t('listingPhotos.deleteConfirmTitle')"
      :message="t('listingPhotos.deleteConfirmMessage')"
      @confirm="handleConfirmDelete"
      @cancel="photoPendingDeletion = null"
    />
  </div>
</template>
