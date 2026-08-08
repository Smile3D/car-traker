<script setup lang="ts">
import { MagnifyingGlassIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import type { Listing } from '~/types/listings'

const emit = defineEmits<{ select: [listing: Listing], close: [] }>()

const { t, n } = useI18n()

const listingStore = useListingStore()

const searchQuery = ref('')

const filteredListings = computed<Listing[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) {
    return listingStore.listings
  }

  return listingStore.listings.filter((listing) =>
    listing.brand.toLowerCase().includes(query)
    || listing.model.toLowerCase().includes(query)
    || listing.year.toLowerCase().includes(query)
  )
})
</script>

<template>
  <BaseModal :title="t('crm.composer.pickerTitle')" @close="emit('close')">
    <div class="space-y-3">
      <div class="relative">
        <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('crm.composer.searchPlaceholder')"
          class="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
      </div>

      <div v-if="filteredListings.length === 0" class="py-8 text-center text-sm text-muted-foreground">
        {{ t('crm.composer.noListingsFound') }}
      </div>

      <ul v-else class="max-h-96 space-y-1 overflow-y-auto">
        <li v-for="listing in filteredListings" :key="listing.id">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-md border border-border p-2 text-left transition-colors hover:bg-muted"
            @click="emit('select', listing)"
          >
            <span class="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <PhotoIcon class="size-5" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-foreground">{{ listing.brand }} {{ listing.model }}, {{ listing.year }}</span>
              <span class="block text-xs text-muted-foreground">{{ n(listing.final_price, 'currency') }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </BaseModal>
</template>
