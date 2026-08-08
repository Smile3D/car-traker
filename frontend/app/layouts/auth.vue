<script setup lang="ts">
import { TruckIcon } from '@heroicons/vue/24/outline'

const { locale, locales, setLocale, t } = useI18n()
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gradient-to-b from-primary/5 via-background to-background px-4 py-10">
    <!-- LocaleSwitcher -->
    <div class="fixed right-4 top-4 flex overflow-hidden rounded-md border border-border bg-surface" role="group" :aria-label="t('nav.appTitle')">
      <button
        v-for="availableLocale in locales"
        :key="availableLocale.code"
        type="button"
        class="px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors"
        :class="locale === availableLocale.code
          ? 'bg-primary text-primary-foreground'
          : 'bg-surface text-muted-foreground hover:bg-muted'"
        @click="setLocale(availableLocale.code)"
      >
        {{ availableLocale.code }}
      </button>
    </div>

    <div class="w-full max-w-sm">
      <!-- BrandMark -->
      <div class="mb-6 flex flex-col items-center gap-2">
        <span class="flex size-11 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
          <TruckIcon class="size-6" />
        </span>
        <h1 class="text-lg font-semibold text-foreground">{{ t('nav.appTitle') }}</h1>
      </div>

      <div class="rounded-lg border border-border bg-surface p-6 shadow-card">
        <slot />
      </div>
    </div>
  </div>
</template>
