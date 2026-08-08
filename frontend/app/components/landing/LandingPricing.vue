<script setup lang="ts">
import { CheckCircleIcon } from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const items = computed(() => (tm('landing.pricing.items') as string[]).map((item) => rt(item)))

const { containerRef } = useScrollReveal()
</script>

<template>
  <section ref="containerRef" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
    <div class="landing-reveal landing-cut-card mx-auto max-w-2xl rounded-3xl border-2 border-[var(--landing-lime)] bg-white p-8 text-center shadow-[0_24px_60px_-24px_rgba(215,255,63,0.5)] sm:p-10">
      <h2 class="landing-display text-2xl font-extrabold uppercase tracking-tight text-[var(--landing-ink)] sm:text-3xl">
        {{ t('landing.pricing.title') }}
      </h2>
      <p class="mt-2 text-sm text-[var(--landing-muted-ink)]">{{ t('landing.pricing.description') }}</p>

      <ul class="mx-auto mt-6 max-w-md space-y-2.5 text-left">
        <li v-for="item in items" :key="item" class="flex items-start gap-2 text-sm text-[var(--landing-ink)]">
          <CheckCircleIcon class="mt-0.5 size-4 shrink-0 text-[var(--landing-pink)]" />
          <span>{{ item }}</span>
        </li>
      </ul>

      <NuxtLink
        to="/register?type=business"
        class="landing-display mt-8 inline-flex cursor-pointer items-center justify-center rounded-full bg-[var(--landing-lime)] px-7 py-3.5 text-sm font-bold uppercase tracking-wide text-[var(--landing-lime-ink)] transition-transform hover:scale-105 sm:text-base"
      >
        {{ t('landing.pricing.ctaButton') }}
      </NuxtLink>
    </div>
  </section>
</template>
