<script setup lang="ts">
import { TruckIcon, UserCircleIcon } from '@heroicons/vue/24/outline'

const { t } = useI18n()

const isRevealed = ref(false)

onMounted(() => {
  requestAnimationFrame(() => {
    isRevealed.value = true
  })
})

const kanbanColumns = computed(() => [
  {
    label: t('landing.hero.mockup.columnFirstContact'),
    cards: [
      { name: t('landing.hero.mockup.card1Name'), car: t('landing.hero.mockup.card1Car') },
    ],
  },
  {
    label: t('landing.hero.mockup.columnViewing'),
    cards: [
      { name: t('landing.hero.mockup.card2Name'), car: t('landing.hero.mockup.card2Car') },
    ],
  },
  {
    label: t('landing.hero.mockup.columnDealClosed'),
    cards: [
      { name: t('landing.hero.mockup.card3Name'), car: t('landing.hero.mockup.card3Car') },
    ],
  },
])
</script>

<template>
  <section class="relative overflow-hidden bg-[var(--landing-cloud)]">
    <!-- AngledBackdrop -->
    <div
      class="absolute inset-0 bg-[var(--landing-void)]"
      style="clip-path: polygon(0 0, 100% 0, 100% 100%, 0 84%)"
    >
      <div class="landing-speed-lines" aria-hidden="true" />
    </div>

    <div class="relative mx-auto grid max-w-7xl gap-12 px-4 pb-28 pt-14 sm:px-6 sm:pt-20 lg:grid-cols-2 lg:items-center lg:pb-36 lg:pt-28">
      <div>
        <h1
          class="landing-display text-4xl font-extrabold uppercase leading-[1.05] tracking-tight text-white transition-all duration-700 sm:text-5xl lg:text-6xl"
          :class="isRevealed ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'"
        >
          {{ t('landing.hero.title') }}
        </h1>
        <p
          class="mt-5 max-w-xl text-base text-[var(--landing-smoke)] transition-all delay-200 duration-700 sm:text-lg"
          :class="isRevealed ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'"
        >
          {{ t('landing.hero.subtitle') }}
        </p>

        <div
          class="mt-8 flex flex-col gap-3 transition-all delay-300 duration-700 sm:flex-row"
          :class="isRevealed ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'"
        >
          <NuxtLink
            to="/register"
            class="landing-display flex cursor-pointer items-center justify-center rounded-full bg-[var(--landing-lime)] px-6 py-3.5 text-sm font-bold uppercase tracking-wide text-[var(--landing-lime-ink)] shadow-[0_0_0_0_rgba(215,255,63,0.6)] transition-all hover:scale-105 hover:shadow-[0_0_32px_4px_rgba(215,255,63,0.45)] sm:text-base"
          >
            {{ t('landing.hero.primaryCta') }}
          </NuxtLink>
          <a
            href="#how-it-works"
            class="flex cursor-pointer items-center justify-center rounded-full border border-white/25 px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:border-[var(--landing-lime)] hover:text-[var(--landing-lime)] sm:text-base"
          >
            {{ t('landing.hero.secondaryCta') }}
          </a>
        </div>

        <p
          class="mt-4 text-sm text-[var(--landing-smoke)] transition-all delay-[400ms] duration-700"
          :class="isRevealed ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'"
        >
          {{ t('landing.hero.socialProof') }}
        </p>
      </div>

      <!-- KanbanMockup: the page's signature element — tilted, cut-corner, idly floating -->
      <div class="flex justify-center lg:justify-end">
        <div class="landing-cut-card landing-float w-full max-w-sm rounded-3xl border border-[var(--landing-border-dark)] bg-[var(--landing-void-soft)] p-4 shadow-[0_20px_60px_-15px_rgba(215,255,63,0.35)] sm:p-5">
          <div class="grid grid-cols-3 gap-2.5">
            <div v-for="column in kanbanColumns" :key="column.label" class="min-w-0 rounded-xl bg-white/5 p-2">
              <p class="truncate px-1 pb-2 text-[10px] font-bold uppercase tracking-wide text-[var(--landing-lime)]">
                {{ column.label }}
              </p>
              <div class="space-y-2">
                <div
                  v-for="card in column.cards"
                  :key="card.name"
                  class="space-y-1.5 rounded-lg border border-white/10 bg-[var(--landing-void)] p-2.5"
                >
                  <p class="flex items-center gap-1 truncate text-xs font-semibold text-white">
                    <UserCircleIcon class="size-3.5 shrink-0 text-[var(--landing-pink)]" />
                    <span class="truncate">{{ card.name }}</span>
                  </p>
                  <p class="flex items-center gap-1 truncate text-[11px] text-[var(--landing-smoke)]">
                    <TruckIcon class="size-3 shrink-0" />
                    <span class="truncate">{{ card.car }}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.landing-speed-lines {
  position: absolute;
  inset: 0;
  overflow: hidden;
  opacity: 0.5;
  background:
    repeating-linear-gradient(
      100deg,
      transparent 0px,
      transparent 90px,
      rgba(215, 255, 63, 0.06) 90px,
      rgba(215, 255, 63, 0.06) 92px
    ),
    repeating-linear-gradient(
      100deg,
      transparent 0px,
      transparent 170px,
      rgba(255, 61, 129, 0.05) 170px,
      rgba(255, 61, 129, 0.05) 173px
    );
}
</style>
