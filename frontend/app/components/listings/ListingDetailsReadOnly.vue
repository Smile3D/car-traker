<script setup lang="ts">
import type { Listing } from '~/types/listings'

const props = defineProps<{ listing: Listing }>()

const { t, n, d } = useI18n()

const formattedDate = (value: string | null): string => value ? d(new Date(value), 'short') : '—'
const formattedPrice = (value: number): string => n(value, 'currency')
</script>

<template>
  <div class="space-y-6">
    <!-- TechnicalSpecsSection -->
    <section class="space-y-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.technicalSection') }}</h2>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.brandLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.brand }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.modelLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.model }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.yearLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.year }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.mileageLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ n(Number(listing.mileage), 'decimal') }} {{ t('common.units.km') }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.vinLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.vin || '—' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.bodyTypeLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ getBodyTypeLabelKey(listing.body_type) ? t(getBodyTypeLabelKey(listing.body_type)!) : listing.body_type }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.transmissionLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ getTransmissionLabelKey(listing.transmission) ? t(getTransmissionLabelKey(listing.transmission)!) : listing.transmission }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.engineLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.engine }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('carForm.fuelTypeLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ t(getListingFuelTypeLabelKey(listing.fuel_type)) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.colorLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ listing.color }}</dd>
        </div>
        <div v-if="listing.trim_level" class="sm:col-span-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.trimLevelLabel') }}</dt>
          <dd class="mt-0.5 whitespace-pre-line text-sm text-foreground">{{ listing.trim_level }}</dd>
        </div>
      </dl>
    </section>

    <!-- ConditionSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.conditionSection') }}</h2>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.conditionLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ t(getListingConditionLabelKey(listing.condition)) }}</dd>
        </div>
        <div v-if="listing.condition_description" class="sm:col-span-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.conditionDescriptionLabel') }}</dt>
          <dd class="mt-0.5 whitespace-pre-line text-sm text-foreground">{{ listing.condition_description }}</dd>
        </div>
      </dl>

      <ListingPhotoGallery :listing-id="listing.id" />
    </section>

    <!-- CommercialSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.commercialSection') }}</h2>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.purchasePriceLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedPrice(listing.purchase_price) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.additionalExpensesLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedPrice(listing.additional_expenses) }}</dd>
        </div>

        <div class="rounded-md bg-muted px-3 py-2 sm:col-span-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.totalCostLabel') }}</dt>
          <dd class="mt-0.5 text-base font-semibold tabular-nums text-foreground">{{ formattedPrice(listing.total_cost) }}</dd>
        </div>

        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.salePriceLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedPrice(listing.sale_price) }}</dd>
        </div>

        <div v-if="listing.discount_amount !== null">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.discountAmountLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedPrice(listing.discount_amount) }}</dd>
        </div>

        <div v-if="listing.discount_amount !== null" class="rounded-md bg-muted px-3 py-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.finalPriceLabel') }}</dt>
          <dd class="mt-0.5 text-base font-semibold tabular-nums text-foreground">{{ formattedPrice(listing.final_price) }}</dd>
        </div>

        <div class="rounded-md bg-primary/5 px-3 py-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.netProfitLabel') }}</dt>
          <dd
            class="mt-0.5 text-base font-semibold tabular-nums"
            :class="listing.net_profit >= 0 ? 'text-success' : 'text-destructive'"
          >
            {{ formattedPrice(listing.net_profit) }}
          </dd>
        </div>
      </dl>
    </section>

    <!-- TimelineSection -->
    <section class="space-y-4 border-t border-border pt-4">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{{ t('listingForm.timelineSection') }}</h2>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.dateAddedLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedDate(listing.date_added) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.deadlineDateLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedDate(listing.deadline_date) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingForm.statusLabel') }}</dt>
          <dd class="mt-0.5">
            <span class="rounded-md px-2 py-0.5 text-xs font-semibold" :class="getListingStatusBadgeClasses(listing.status)">
              {{ t(`listingStatus.${listing.status}`) }}
            </span>
          </dd>
        </div>
        <div v-if="listing.date_sold">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('listingDetails.soldOn') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ formattedDate(listing.date_sold) }}</dd>
        </div>
      </dl>
    </section>
  </div>
</template>
