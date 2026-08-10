<script setup lang="ts">
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'

defineOptions({ inheritAttrs: false })

defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()

const { t } = useI18n()

const isPasswordVisible = ref(false)

function togglePasswordVisibility(): void {
  isPasswordVisible.value = !isPasswordVisible.value
}
</script>

<template>
  <div class="relative mt-1.5">
    <input
      :value="modelValue"
      v-bind="$attrs"
      :type="isPasswordVisible ? 'text' : 'password'"
      class="w-full rounded-md border border-border bg-surface px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    >
    <button
      type="button"
      class="absolute right-2 top-1/2 -translate-y-1/2 rounded text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
      :aria-label="isPasswordVisible ? t('common.buttons.hidePassword') : t('common.buttons.showPassword')"
      :title="isPasswordVisible ? t('common.buttons.hidePassword') : t('common.buttons.showPassword')"
      @click="togglePasswordVisibility"
    >
      <EyeSlashIcon v-if="isPasswordVisible" class="size-4" />
      <EyeIcon v-else class="size-4" />
    </button>
  </div>
</template>
