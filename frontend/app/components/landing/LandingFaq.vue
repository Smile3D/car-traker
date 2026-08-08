<script setup lang="ts">
import { ChevronDownIcon } from '@heroicons/vue/24/outline'

const { t, tm, rt } = useI18n()

const items = computed(() => (tm('landing.faq.items') as { question: string, answer: string }[]).map(
  (item) => ({ question: rt(item.question), answer: rt(item.answer) })
))

const openIndex = ref<number | null>(0)

function toggleItem(index: number): void {
  openIndex.value = openIndex.value === index ? null : index
}

const { containerRef } = useScrollReveal()
</script>

<template>
  <section id="faq" ref="containerRef" class="border-t border-[var(--landing-border-light)]">
    <div class="mx-auto max-w-3xl px-4 py-16 sm:px-6 sm:py-24">
      <h2 class="landing-reveal landing-display text-center text-2xl font-extrabold uppercase tracking-tight text-[var(--landing-ink)] sm:text-3xl">
        {{ t('landing.faq.title') }}
      </h2>

      <div class="landing-reveal landing-cut-card mt-8 divide-y divide-[var(--landing-border-light)] rounded-2xl border border-[var(--landing-border-light)] bg-white">
        <div v-for="(item, index) in items" :key="item.question">
          <button
            type="button"
            class="flex w-full cursor-pointer items-center justify-between gap-4 px-5 py-4 text-left text-sm font-semibold text-[var(--landing-ink)]"
            :aria-expanded="openIndex === index"
            @click="toggleItem(index)"
          >
            {{ item.question }}
            <ChevronDownIcon
              class="size-4 shrink-0 text-[var(--landing-pink)] transition-transform"
              :class="{ 'rotate-180': openIndex === index }"
            />
          </button>
          <p v-if="openIndex === index" class="px-5 pb-4 text-sm text-[var(--landing-muted-ink)]">
            {{ item.answer }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
