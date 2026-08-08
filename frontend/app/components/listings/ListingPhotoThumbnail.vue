<script setup lang="ts">
import { PhotoIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type { ListingPhoto } from '~/types/listingPhotos'

const props = withDefaults(defineProps<{
  listingId?: number
  photo?: ListingPhoto
  previewUrl?: string
  isCover: boolean
  isEditMode?: boolean
}>(), {
  isEditMode: false,
})

const emit = defineEmits<{ open: [imageUrl: string], delete: [] }>()

const { t } = useI18n()

const listingPhotoStore = useListingPhotoStore()

// Staging mode passes an already-created (parent-owned) object URL via
// previewUrl — nothing to fetch, and revoking it here would be wrong since
// the parent's staged-files list controls that URL's lifetime.
const fetchedImageUrl = ref<string | null>(null)

onMounted(async () => {
  if (props.previewUrl !== undefined || props.listingId === undefined || props.photo === undefined) {
    return
  }
  try {
    fetchedImageUrl.value = await listingPhotoStore.fetchPhotoImageUrl(props.listingId, props.photo.id)
  } catch {
    // placeholder icon shown instead
  }
})

onUnmounted(() => {
  if (fetchedImageUrl.value) {
    URL.revokeObjectURL(fetchedImageUrl.value)
  }
})

const displayImageUrl = computed<string | null>(() => props.previewUrl ?? fetchedImageUrl.value)
</script>

<template>
  <div
    class="group relative size-24 shrink-0 overflow-hidden rounded-md border border-border bg-surface"
    :class="isEditMode ? 'cursor-grab active:cursor-grabbing' : ''"
  >
    <span
      v-if="isCover"
      class="absolute left-1 top-1 z-10 rounded bg-primary px-1.5 py-0.5 text-xs font-semibold text-primary-foreground"
    >
      {{ t('listingPhotos.coverBadge') }}
    </span>

    <button
      type="button"
      class="flex size-full items-center justify-center overflow-hidden bg-muted disabled:cursor-default"
      :disabled="!displayImageUrl"
      @click="displayImageUrl && emit('open', displayImageUrl)"
    >
      <img v-if="displayImageUrl" :src="displayImageUrl" class="size-full object-cover transition-transform group-hover:scale-105" alt="">
      <PhotoIcon v-else class="size-6 text-muted-foreground" />
    </button>

    <button
      v-if="isEditMode"
      type="button"
      class="absolute right-1 top-1 z-10 flex size-6 items-center justify-center rounded-md bg-slate-900/60 text-white opacity-0 transition-opacity hover:bg-destructive group-hover:opacity-100"
      :aria-label="t('common.buttons.delete')"
      @click="emit('delete')"
    >
      <TrashIcon class="size-3.5" />
    </button>
  </div>
</template>
