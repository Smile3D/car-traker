<script setup lang="ts">
import { TruckIcon } from '@heroicons/vue/24/outline'
import type { ListingPhoto } from '~/types/listingPhotos'

const props = withDefaults(defineProps<{
  listingId: number
  size?: 'sm' | 'md'
}>(), {
  size: 'md',
})

// Bypasses listingPhotoStore on purpose: that store holds the photo list for
// a single actively-managed gallery (the detail page). Cover thumbnails are
// rendered many-at-once across a list of listings (inventory rows, client
// cards), so each instance fetches independently instead of sharing — and
// clobbering — one global "current listing's photos" ref.
const { apiGet, apiGetBlob } = useApi()

const coverImageUrl = ref<string | null>(null)

onMounted(async () => {
  try {
    const photos = await apiGet<ListingPhoto[]>(`/listings/${props.listingId}/photos`)
    const coverPhoto = photos[0]
    if (coverPhoto) {
      const imageBlob = await apiGetBlob(`/listings/${props.listingId}/photos/${coverPhoto.id}/file`)
      coverImageUrl.value = URL.createObjectURL(imageBlob)
    }
  } catch {
    // no cover photo available; placeholder icon shown instead
  }
})

onUnmounted(() => {
  if (coverImageUrl.value) {
    URL.revokeObjectURL(coverImageUrl.value)
  }
})
</script>

<template>
  <div
    class="flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-muted"
    :class="size === 'sm' ? 'size-8' : 'size-11'"
  >
    <img v-if="coverImageUrl" :src="coverImageUrl" class="size-full object-cover" alt="">
    <TruckIcon v-else class="text-muted-foreground" :class="size === 'sm' ? 'size-4' : 'size-5'" />
  </div>
</template>
