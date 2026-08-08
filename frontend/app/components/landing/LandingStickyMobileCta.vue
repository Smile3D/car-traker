<script setup lang="ts">
const { t } = useI18n()

const isVisible = ref(false)

function handleScroll(): void {
  isVisible.value = window.scrollY > window.innerHeight * 0.6
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div
    v-if="isVisible"
    class="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--landing-border-dark)] bg-[var(--landing-void)] p-3 sm:hidden"
  >
    <NuxtLink
      to="/register?type=business"
      class="landing-display flex w-full cursor-pointer items-center justify-center rounded-full bg-[var(--landing-lime)] px-4 py-3.5 text-sm font-bold uppercase tracking-wide text-[var(--landing-lime-ink)]"
    >
      {{ t('landing.stickyCta.button') }}
    </NuxtLink>
  </div>
</template>
