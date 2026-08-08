<script setup lang="ts">
import {
  RectangleStackIcon,
  CameraIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  PresentationChartLineIcon,
  PaperAirplaneIcon,
} from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const icons = [RectangleStackIcon, CameraIcon, UserGroupIcon, CurrencyDollarIcon, PresentationChartLineIcon, PaperAirplaneIcon]

const items = computed(() => (tm('landing.features.items') as { title: string, description: string }[]).map(
  (item, index) => ({ title: rt(item.title), description: rt(item.description), icon: icons[index] })
))

const { containerRef } = useScrollReveal()
</script>

<template>
  <section id="features" ref="containerRef" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
    <h2 class="landing-reveal landing-display text-center text-2xl font-extrabold uppercase tracking-tight text-[var(--landing-ink)] sm:text-3xl">
      {{ t('landing.features.title') }}
    </h2>

    <div class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="(item, index) in items"
        :key="item.title"
        class="landing-reveal landing-cut-card landing-cut-card-sm rounded-2xl border border-[var(--landing-border-light)] bg-white p-5 transition-[border-color,box-shadow] duration-300 hover:border-[var(--landing-lime)] hover:shadow-[0_16px_32px_-16px_rgba(27,22,38,0.3)]"
        :style="{ transitionDelay: `${(index % 3) * 80}ms` }"
      >
        <span class="flex size-11 items-center justify-center rounded-full bg-[var(--landing-lime)] text-[var(--landing-lime-ink)]">
          <component :is="item.icon" class="size-5" />
        </span>
        <p class="landing-display mt-4 text-sm font-bold text-[var(--landing-ink)]">{{ item.title }}</p>
        <p class="mt-1.5 text-sm text-[var(--landing-muted-ink)]">{{ item.description }}</p>
      </div>
    </div>
  </section>
</template>
