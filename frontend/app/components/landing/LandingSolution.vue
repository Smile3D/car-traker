<script setup lang="ts">
import { PlusCircleIcon, InboxArrowDownIcon, ArrowsRightLeftIcon, CheckBadgeIcon } from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const icons = [PlusCircleIcon, InboxArrowDownIcon, ArrowsRightLeftIcon, CheckBadgeIcon]

const steps = computed(() => (tm('landing.solution.steps') as { title: string, description: string }[]).map(
  (step, index) => ({ title: rt(step.title), description: rt(step.description), icon: icons[index] })
))

const { containerRef } = useScrollReveal()
</script>

<template>
  <section id="how-it-works" ref="containerRef" class="bg-[var(--landing-void)]">
    <div class="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <h2 class="landing-reveal landing-display text-center text-2xl font-extrabold uppercase tracking-tight text-white sm:text-3xl">
        {{ t('landing.solution.title') }}
      </h2>

      <div class="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="(step, index) in steps"
          :key="step.title"
          class="landing-reveal relative"
          :style="{ transitionDelay: `${index * 90}ms` }"
        >
          <span class="landing-display block text-5xl font-black text-[var(--landing-void-soft)] [-webkit-text-stroke:1.5px_var(--landing-lime)]">
            {{ String(index + 1).padStart(2, '0') }}
          </span>
          <component :is="step.icon" class="mt-2 size-6 text-[var(--landing-pink)]" />
          <p class="landing-display mt-4 text-sm font-bold uppercase tracking-wide text-white">{{ step.title }}</p>
          <p class="mt-1.5 text-sm text-[var(--landing-smoke)]">{{ step.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
