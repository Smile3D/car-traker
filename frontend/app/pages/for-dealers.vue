<script setup lang="ts">
definePageMeta({ layout: 'landing' })

const { t } = useI18n()

useSeoMeta({
  title: () => t('landing.meta.title'),
  description: () => t('landing.meta.description'),
  ogTitle: () => t('landing.meta.title'),
  ogDescription: () => t('landing.meta.description'),
  ogType: 'website',
})
</script>

<template>
  <div>
    <LandingHero />
    <LandingProblem />
    <LandingSolution />
    <LandingFeatures />
    <LandingComparison />
    <LandingPricing />
    <LandingFaq />
    <LandingCta />
  </div>
</template>
