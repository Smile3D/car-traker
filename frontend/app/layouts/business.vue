<script setup lang="ts">
import {
  ArchiveBoxIcon,
  ArrowRightOnRectangleIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  FlagIcon,
  IdentificationIcon,
  PaperAirplaneIcon,
  PlusCircleIcon,
  Squares2X2Icon,
  TruckIcon,
  UsersIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()
const currencyStore = useCurrencyStore()
const router = useRouter()
const route = useRoute()
const { locale, locales, setLocale, t } = useI18n()

const { isCompanyAdmin } = useUserRole()

// Fire-and-forget: cached in the store after the first successful/failed
// attempt for the session, so navigating between pages never re-hits
// GET /currency/rate. Skipped entirely for accounts with no company (the
// endpoint would just 403).
if (authStore.user?.company_id) {
  void currencyStore.fetchRate()
}

// Purely a reference value shown next to the profile chip — never shown at
// all if neither an auto nor a manual rate is available yet.
const currencyRateDisplay = computed<string | null>(() => {
  const activeRate = currencyStore.rate?.active_rate
  return activeRate == null ? null : t('nav.currencyRateDisplay', { rate: activeRate.toFixed(2) })
})

const allNavItems = [
  { to: '/crm', labelKey: 'crm.sidebar.dashboard', icon: Squares2X2Icon, activeRouteNames: ['crm'], ownerOnly: false },
  { to: '/crm/inventory', labelKey: 'crm.sidebar.inventory', icon: TruckIcon, activeRouteNames: ['crm-inventory', 'crm-inventory-id'], ownerOnly: false },
  { to: '/crm/inventory/new', labelKey: 'crm.sidebar.addCar', icon: PlusCircleIcon, activeRouteNames: ['crm-inventory-new'], ownerOnly: false },
  { to: '/crm/archive', labelKey: 'crm.sidebar.archive', icon: ArchiveBoxIcon, activeRouteNames: ['crm-archive'], ownerOnly: false },
  { to: '/crm/service', labelKey: 'crm.sidebar.service', icon: WrenchScrewdriverIcon, activeRouteNames: ['crm-service'], ownerOnly: false },
  { to: '/crm/deal-history', labelKey: 'crm.sidebar.dealHistory', icon: ClipboardDocumentListIcon, activeRouteNames: ['crm-deal-history'], ownerOnly: false },
  { to: '/crm/clients', labelKey: 'crm.sidebar.clients', icon: UsersIcon, activeRouteNames: ['crm-clients'], ownerOnly: false },
  { to: '/crm/employees', labelKey: 'crm.sidebar.employees', icon: IdentificationIcon, activeRouteNames: ['crm-employees'], ownerOnly: false },
  { to: '/crm/sales-plans', labelKey: 'crm.sidebar.salesPlans', icon: FlagIcon, activeRouteNames: ['crm-sales-plans'], ownerOnly: false },
  { to: '/crm/composer', labelKey: 'crm.sidebar.composer', icon: PaperAirplaneIcon, activeRouteNames: ['crm-composer'], ownerOnly: false },
  { to: '/crm/analytics', labelKey: 'crm.sidebar.analytics', icon: ChartBarIcon, activeRouteNames: ['crm-analytics'], ownerOnly: false },
  { to: '/settings', labelKey: 'crm.sidebar.settings', icon: Cog6ToothIcon, activeRouteNames: ['settings'], ownerOnly: false },
]

const navItems = computed(() => allNavItems.filter((navItem) => !navItem.ownerOnly || isCompanyAdmin.value))

function isActiveNavItem(navItem: typeof allNavItems[number]): boolean {
  return navItem.activeRouteNames.includes(String(route.name))
}

function handleLogoutClick(): void {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex min-h-screen bg-background">
    <!-- Sidebar -->
    <aside class="hidden w-60 shrink-0 flex-col border-r border-border bg-surface sm:flex">
      <div class="flex items-center gap-2 border-b border-border px-4 py-4">
        <span class="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <TruckIcon class="size-5" />
        </span>
        <span class="text-base font-semibold text-foreground">{{ t('nav.appTitle') }}</span>
      </div>

      <nav class="flex-1 space-y-1 p-3">
        <NuxtLink
          v-for="navItem in navItems"
          :key="navItem.to"
          :to="navItem.to"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors"
          :class="isActiveNavItem(navItem)
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          <component :is="navItem.icon" class="size-5" />
          {{ t(navItem.labelKey) }}
        </NuxtLink>
      </nav>
    </aside>

    <div class="flex flex-1 flex-col">
      <header class="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
        <div class="flex items-center justify-end gap-2 px-4 py-3 sm:gap-4 sm:px-6">
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

          <!-- CurrencyRate -->
          <div
            v-if="currencyRateDisplay"
            class="hidden items-center rounded-md border border-border bg-muted/50 px-2.5 py-1.5 text-sm font-medium text-foreground sm:flex"
          >
            {{ currencyRateDisplay }}
          </div>

          <!-- UserChip -->
          <div class="hidden items-center gap-2 sm:flex">
            <UserAvatar />
            <span class="max-w-[12rem] truncate text-sm text-muted-foreground">{{ authStore.user?.email }}</span>
          </div>

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
      </header>

      <main class="flex-1 px-4 py-6 sm:px-6">
        <slot />
      </main>
    </div>
  </div>
</template>
