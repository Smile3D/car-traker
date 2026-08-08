<script setup lang="ts">
import { XMarkIcon, CheckIcon } from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const withoutItems = computed(() => (tm('landing.comparison.withoutItems') as string[]).map((item) => rt(item)))
const withItems = computed(() => (tm('landing.comparison.withItems') as string[]).map((item) => rt(item)))

const { containerRef } = useScrollReveal()
</script>

<template>
  <section ref="containerRef" class="bg-[var(--landing-void)]">
    <div class="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <h2 class="landing-reveal landing-display text-center text-2xl font-extrabold uppercase tracking-tight text-white sm:text-3xl">
        {{ t('landing.comparison.title') }}
      </h2>

      <div class="mt-10 grid gap-5 sm:grid-cols-2">
        <div class="landing-reveal rounded-2xl border border-white/10 bg-white/[0.03] p-6 opacity-90">
          <p class="landing-display text-sm font-bold uppercase tracking-wide text-[var(--landing-smoke)]">{{ t('landing.comparison.withoutTitle') }}</p>
          <ul class="mt-4 space-y-3">
            <li v-for="item in withoutItems" :key="item" class="flex items-start gap-2 text-sm text-[var(--landing-smoke)]">
              <XMarkIcon class="mt-0.5 size-4 shrink-0 text-[var(--landing-pink)]" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>

        <div
          class="landing-reveal landing-cut-card rounded-2xl border border-[var(--landing-lime)]/40 bg-[var(--landing-void-soft)] p-6 shadow-[0_20px_50px_-20px_rgba(215,255,63,0.3)]"
          style="transition-delay: 120ms"
        >
          <p class="landing-display text-sm font-bold uppercase tracking-wide text-[var(--landing-lime)]">{{ t('landing.comparison.withTitle') }}</p>
          <ul class="mt-4 space-y-3">
            <li v-for="item in withItems" :key="item" class="flex items-start gap-2 text-sm text-white">
              <CheckIcon class="mt-0.5 size-4 shrink-0 text-[var(--landing-lime)]" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
