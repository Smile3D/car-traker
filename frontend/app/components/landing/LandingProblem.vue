<script setup lang="ts">
import { ChatBubbleLeftRightIcon, ChartBarIcon, ClockIcon, UserMinusIcon } from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const icons = [ChatBubbleLeftRightIcon, ClockIcon, UserMinusIcon, ChartBarIcon]

const items = computed(() => (tm('landing.problem.items') as { title: string, description: string }[]).map(
  (item, index) => ({ title: rt(item.title), description: rt(item.description), icon: icons[index] })
))

const { containerRef } = useScrollReveal()
</script>

<template>
  <section ref="containerRef" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
    <h2 class="landing-reveal landing-display text-center text-2xl font-extrabold uppercase tracking-tight text-[var(--landing-ink)] sm:text-3xl">
      {{ t('landing.problem.title') }}
    </h2>

    <div class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <div
        v-for="(item, index) in items"
        :key="item.title"
        class="landing-reveal landing-cut-card landing-cut-card-sm rounded-2xl border border-[var(--landing-border-light)] bg-white p-5 transition-[border-color,box-shadow] duration-300 hover:border-[var(--landing-lime)] hover:shadow-[0_16px_32px_-16px_rgba(27,22,38,0.3)]"
        :style="{ transitionDelay: `${index * 80}ms` }"
      >
        <span
          class="flex size-11 items-center justify-center rounded-full"
          :class="index % 2 === 0 ? 'bg-[var(--landing-pink)]/10 text-[var(--landing-pink)]' : 'bg-[var(--landing-ink)]/10 text-[var(--landing-ink)]'"
        >
          <component :is="item.icon" class="size-5" />
        </span>
        <p class="landing-display mt-4 text-sm font-bold text-[var(--landing-ink)]">{{ item.title }}</p>
        <p class="mt-1.5 text-sm text-[var(--landing-muted-ink)]">{{ item.description }}</p>
      </div>
    </div>
  </section>
</template>
