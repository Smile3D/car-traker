<script setup lang="ts">
const { t } = useI18n()

const { containerRef } = useScrollReveal()
</script>

<template>
  <section ref="containerRef" class="relative overflow-hidden bg-[var(--landing-cloud)]">
    <div
      class="absolute inset-0 bg-[var(--landing-void)]"
      style="clip-path: polygon(0 14%, 100% 0, 100% 100%, 0 100%)"
    />

    <div class="landing-reveal relative mx-auto flex max-w-4xl flex-col items-center gap-6 px-4 pb-16 pt-24 text-center sm:px-6 sm:pb-24 sm:pt-32">
      <h2 class="landing-display text-2xl font-extrabold uppercase leading-tight tracking-tight text-white sm:text-4xl">
        {{ t('landing.finalCta.title') }}
      </h2>
      <NuxtLink
        to="/register"
        class="landing-display inline-flex cursor-pointer items-center justify-center rounded-full bg-[var(--landing-lime)] px-7 py-3.5 text-sm font-bold uppercase tracking-wide text-[var(--landing-lime-ink)] shadow-[0_0_40px_-4px_rgba(215,255,63,0.5)] transition-transform hover:scale-105 sm:text-base"
      >
        {{ t('landing.finalCta.ctaButton') }}
      </NuxtLink>
    </div>
  </section>
</template>
