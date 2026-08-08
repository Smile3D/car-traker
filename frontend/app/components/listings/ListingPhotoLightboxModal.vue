<script setup lang="ts">
defineProps<{ imageUrl: string }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
</script>

<template>
  <BaseModal :title="t('listingPhotos.title')" max-width="lg" @close="emit('close')">
    <img :src="imageUrl" class="max-h-[70vh] w-full rounded-md object-contain" alt="">
  </BaseModal>
</template>
