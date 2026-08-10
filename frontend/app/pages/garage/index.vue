<script setup lang="ts">
import { BuildingOfficeIcon, PlusIcon, TruckIcon } from '@heroicons/vue/24/outline'

definePageMeta({ middleware: 'garage-disabled' })

const { t } = useI18n()

const authStore = useAuthStore()
const carsStore = useCarStore()

const isAddCarModalOpen = ref(false)

await carsStore.fetchListCars()

const { isOwner } = useUserRole()
const showBusinessProfileBanner = computed<boolean>(() =>
  isOwner.value && !authStore.user?.company?.name
)
</script>

<template>
  <div class="space-y-6">
    <!-- BusinessProfileBanner -->
    <div
      v-if="showBusinessProfileBanner"
      class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3"
    >
      <div class="flex items-center gap-2">
        <BuildingOfficeIcon class="size-5 shrink-0 text-primary" />
        <p class="text-sm text-foreground">{{ t('garage.businessBannerText') }}</p>
      </div>
      <NuxtLink
        to="/settings"
        class="whitespace-nowrap rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
      >
        {{ t('garage.businessBannerLink') }}
      </NuxtLink>
    </div>

    <!-- ===== GarageStatsRow ===== -->
    <!-- StatTile -->
    <div class="flex w-fit items-center gap-3 rounded-lg border border-border bg-surface p-4 shadow-card">
      <span class="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
        <TruckIcon class="size-5" />
      </span>
      <div>
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('garage.totalCars') }}</p>
        <p class="text-xl font-semibold tabular-nums text-foreground">{{ carsStore.cars.length }}</p>
      </div>
    </div>

    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold text-foreground">{{ t('garage.title') }}</h1>

        <button
          type="button"
          class="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
          @click="isAddCarModalOpen = true"
        >
          <PlusIcon class="size-4" />
          {{ t('garage.addCar') }}
        </button>
      </div>

      <!-- GarageEmptyState -->
      <div
        v-if="carsStore.cars.length === 0"
        class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center"
      >
        <span class="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <TruckIcon class="size-6" />
        </span>
        <div>
          <p class="font-medium text-foreground">{{ t('garage.emptyTitle') }}</p>
          <p class="mt-1 text-sm text-muted-foreground">{{ t('garage.emptySubtitle') }}</p>
        </div>
        <button
          type="button"
          class="mt-2 flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover"
          @click="isAddCarModalOpen = true"
        >
          <PlusIcon class="size-4" />
          {{ t('garage.addCar') }}
        </button>
      </div>

      <!-- CarGrid -->
      <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <CarCard
          v-for="car in carsStore.cars"
          :key="car.id"
          :id="car.id"
          :brand="car.brand"
          :model="car.model"
          :year="car.year"
          :mileage="car.mileage"
          :vin="car.vin"
          :created_at="car.created_at"
        />
      </div>
    </section>

    <AddCarModal v-if="isAddCarModalOpen" @close="isAddCarModalOpen = false" />
  </div>
</template>
