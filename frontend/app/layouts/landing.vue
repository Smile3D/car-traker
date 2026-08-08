<script setup lang="ts">
useHead({
  link: [
    { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
    { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Unbounded:wght@400;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap',
    },
  ],
})
</script>

<template>
  <div class="landing-page">
    <LandingHeader />
    <main>
      <slot />
    </main>
    <LandingFooter />
    <LandingStickyMobileCta />
  </div>
</template>

<style>
/* Design tokens scoped to the /for-dealers marketing page only — deliberately
   isolated from the CRM's tokens in main.css/tailwind.config.ts. Unscoped so
   the custom properties and utility classes below reach every child
   component, but every selector is prefixed by .landing-page so nothing
   leaks into the rest of the app. */
.landing-page {
  --landing-void: #16121f;
  --landing-void-soft: #201a2e;
  --landing-cloud: #f7f5fa;
  --landing-cloud-card: #ffffff;
  --landing-ink: #1b1626;
  --landing-lime: #d7ff3f;
  --landing-lime-ink: #16121f;
  --landing-pink: #ff3d81;
  --landing-smoke: #8b84a0;
  --landing-muted-ink: #6b6380;
  --landing-border-dark: rgba(215, 255, 63, 0.16);
  --landing-border-light: rgba(27, 22, 38, 0.1);
  --landing-cut: 22px;

  font-family: 'Manrope', ui-sans-serif, system-ui, sans-serif;
  background: var(--landing-cloud);
  color: var(--landing-ink);
}

.landing-page .landing-display {
  font-family: 'Unbounded', ui-sans-serif, system-ui, sans-serif;
}

/* Signature shape: one clipped corner, used on hero mockup, feature/problem
   cards and the FAQ panel so it reads as this page's visual "signature". */
.landing-page .landing-cut-card {
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - var(--landing-cut)), calc(100% - var(--landing-cut)) 100%, 0 100%);
}

.landing-page .landing-cut-card-sm {
  --landing-cut: 14px;
}

.landing-page .landing-float {
  animation: landing-float 5s ease-in-out infinite;
}

@keyframes landing-float {
  0%, 100% { transform: translateY(0) rotate(-3deg); }
  50% { transform: translateY(-12px) rotate(-1.5deg); }
}

.landing-page .landing-reveal {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.landing-page .landing-reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .landing-page .landing-float {
    animation: none;
  }

  .landing-page .landing-reveal {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
