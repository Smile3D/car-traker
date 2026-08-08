<script setup lang="ts">
import { TruckIcon, ArrowRightOnRectangleIcon, Cog6ToothIcon } from '@heroicons/vue/24/outline'

const authStore = useAuthStore()
const router = useRouter()
const { locale, locales, setLocale, t } = useI18n()

function handleLogoutClick(): void {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-background">
    <header class="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <!-- BrandMark -->
        <div class="flex items-center gap-2">
          <span class="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <TruckIcon class="size-5" />
          </span>
          <span class="hidden text-base font-semibold text-foreground sm:inline">{{ t('nav.appTitle') }}</span>
        </div>

        <div class="flex items-center gap-2 sm:gap-4">
          <!-- LocaleSwitcher -->
          <div class="flex overflow-hidden rounded-md border border-border" role="group" :aria-label="t('nav.appTitle')">
            <button
              v-for="availableLocale in locales"
              :key="availableLocale.code"
              type="button"
              class="px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors"
              :class="locale === availableLocale.code
                ? 'bg-primary text-primary-foreground'
                : 'bg-surface text-muted-foreground hover:bg-muted'"
              @click="setLocale(availableLocale.code)"
            >
              {{ availableLocale.code }}
            </button>
          </div>

          <!-- UserChip -->
          <div class="hidden items-center gap-2 sm:flex">
            <UserAvatar />
            <span class="max-w-[12rem] truncate text-sm text-muted-foreground">{{ authStore.user?.email }}</span>
          </div>

          <NuxtLink
            to="/settings"
            class="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            :aria-label="t('nav.settings')"
            :title="t('nav.settings')"
          >
            <Cog6ToothIcon class="size-5" />
          </NuxtLink>

          <button
            type="button"
            class="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-destructive"
            :aria-label="t('nav.logout')"
            :title="t('nav.logout')"
            @click="handleLogoutClick"
          >
            <ArrowRightOnRectangleIcon class="size-5" />
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <slot />
    </main>
  </div>
</template>
