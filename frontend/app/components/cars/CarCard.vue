<script setup lang="ts">
import { TruckIcon, TrashIcon } from '@heroicons/vue/24/outline'

interface CarProps {
  id: number
  brand: string
  model: string
  year: string
  mileage: string
  vin: string
  created_at: string
}

const props = defineProps<CarProps>()

const { t, n, d } = useI18n()

const router = useRouter()
const carsStore = useCarStore()

const deleteCar = async (carId: number) => {
  await carsStore.deleteCar(carId)
}

function handleCardClick(): void {
  router.push(`/garage/${props.id}`)
}

const formattedMileage = computed<string>(() => n(Number(props.mileage), 'decimal'))
const formattedCreatedAt = computed<string>(() => d(new Date(props.created_at), 'short'))
</script>

<template>
  <article
    class="group cursor-pointer rounded-lg border border-border bg-surface p-4 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-elevated"
    @click="handleCardClick"
  >
    <!-- CarCardHeader -->
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-start gap-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <TruckIcon class="size-5" />
        </span>
        <div>
          <h2 class="text-sm font-semibold leading-tight text-foreground">{{ props.brand }} {{ props.model }}</h2>
          <span class="text-xs text-muted-foreground">{{ props.year }}</span>
        </div>
      </div>

      <button
        type="button"
        class="-m-1 flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        :aria-label="t('common.buttons.delete')"
        @click.stop="deleteCar(id)"
      >
        <TrashIcon class="size-4" />
      </button>
    </div>

    <!-- CarCardMeta -->
    <dl class="mt-4 space-y-1.5 border-t border-border pt-3 text-sm">
      <div class="flex justify-between">
        <dt class="text-muted-foreground">{{ t('common.mileage') }}</dt>
        <dd class="font-medium tabular-nums text-foreground">{{ formattedMileage }} {{ t('common.units.km') }}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-muted-foreground">{{ t('common.vin') }}</dt>
        <dd class="font-medium text-foreground">{{ props.vin }}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-muted-foreground">{{ t('common.addedAt') }}</dt>
        <dd class="font-medium text-foreground">{{ formattedCreatedAt }}</dd>
      </div>
    </dl>
  </article>
</template>
