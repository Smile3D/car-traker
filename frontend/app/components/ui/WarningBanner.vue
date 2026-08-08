<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <div
    class="flex items-start gap-3 rounded-lg border border-accent/30 border-l-4 border-l-accent bg-accent/10 p-4 text-sm text-accent"
    role="alert"
  >
    <ExclamationTriangleIcon class="mt-0.5 size-5 shrink-0" />
    <p><slot /></p>
  </div>
</template>
