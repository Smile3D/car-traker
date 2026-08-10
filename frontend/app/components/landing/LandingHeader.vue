<script setup lang="ts">
import { BoltIcon } from '@heroicons/vue/24/outline'

const { locale, locales, setLocale, t } = useI18n()
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-[var(--landing-border-dark)] bg-[var(--landing-void)]/90 backdrop-blur">
    <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
      <!-- BrandMark -->
      <NuxtLink to="/for-dealers" class="flex items-center gap-2">
        <span class="flex size-9 items-center justify-center rounded-full bg-[var(--landing-lime)] text-[var(--landing-lime-ink)]">
          <BoltIcon class="size-5" />
        </span>
        <span class="landing-display hidden text-sm font-bold uppercase tracking-wide text-white sm:inline">{{ t('nav.appTitle') }}</span>
      </NuxtLink>

      <!-- PrimaryNav -->
      <nav class="hidden items-center gap-6 text-sm font-medium text-[var(--landing-smoke)] md:flex">
        <a href="#features" class="transition-colors hover:text-[var(--landing-lime)]">{{ t('landing.header.navFeatures') }}</a>
        <a href="#how-it-works" class="transition-colors hover:text-[var(--landing-lime)]">{{ t('landing.header.navHowItWorks') }}</a>
        <a href="#faq" class="transition-colors hover:text-[var(--landing-lime)]">{{ t('landing.header.navFaq') }}</a>
      </nav>

      <div class="flex items-center gap-2 sm:gap-3">
        <!-- LocaleSwitcher -->
        <div class="hidden overflow-hidden rounded-full border border-[var(--landing-border-dark)] sm:flex" role="group" :aria-label="t('nav.appTitle')">
          <button
            v-for="availableLocale in locales"
            :key="availableLocale.code"
            type="button"
            class="cursor-pointer px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors"
            :class="locale === availableLocale.code
              ? 'bg-[var(--landing-lime)] text-[var(--landing-lime-ink)]'
              : 'text-[var(--landing-smoke)] hover:text-white'"
            @click="setLocale(availableLocale.code)"
          >
            {{ availableLocale.code }}
          </button>
        </div>

        <NuxtLink
          to="/register"
          class="landing-display cursor-pointer rounded-full bg-[var(--landing-lime)] px-4 py-2 text-xs font-bold uppercase tracking-wide text-[var(--landing-lime-ink)] transition-transform hover:scale-105"
        >
          {{ t('landing.header.ctaButton') }}
        </NuxtLink>
      </div>
    </div>
  </header>
</template>
