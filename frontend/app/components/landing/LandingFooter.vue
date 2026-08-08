<script setup lang="ts">
import { BoltIcon } from '@heroicons/vue/24/outline'

const { t } = useI18n()

const currentYear = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-[var(--landing-border-dark)] bg-[var(--landing-void)]">
    <div class="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6">
      <div class="flex items-center gap-2">
        <span class="flex size-7 items-center justify-center rounded-full bg-[var(--landing-lime)] text-[var(--landing-lime-ink)]">
          <BoltIcon class="size-4" />
        </span>
        <span class="landing-display text-xs font-bold uppercase tracking-wide text-white">{{ t('nav.appTitle') }}</span>
      </div>

      <nav class="flex items-center gap-6 text-sm text-[var(--landing-smoke)]">
        <a href="#features" class="transition-colors hover:text-[var(--landing-lime)]">{{ t('landing.footer.about') }}</a>
        <a href="#faq" class="transition-colors hover:text-[var(--landing-lime)]">{{ t('landing.footer.contacts') }}</a>
      </nav>

      <p class="text-xs text-[var(--landing-smoke)]">{{ t('landing.footer.copyright', { year: currentYear }) }}</p>
    </div>
  </footer>
</template>
