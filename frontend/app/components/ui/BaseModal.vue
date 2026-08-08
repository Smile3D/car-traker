<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline'

withDefaults(defineProps<{
  title: string
  maxWidth?: 'md' | 'lg'
}>(), {
  maxWidth: 'md',
})

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div
        class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg bg-surface shadow-elevated"
        :class="maxWidth === 'lg' ? 'max-w-lg' : 'max-w-md'"
      >
        <!-- ModalHeader -->
        <div class="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 class="text-base font-semibold text-foreground">{{ title }}</h2>

          <button
            type="button"
            class="-m-1.5 flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            :aria-label="t('common.buttons.close')"
            @click="emit('close')"
          >
            <XMarkIcon class="size-5" />
          </button>
        </div>

        <!-- ModalBody -->
        <div class="overflow-y-auto px-6 py-4">
          <slot />
        </div>

        <!-- ModalFooter -->
        <div v-if="$slots.footer" class="flex gap-2 border-t border-border px-6 py-4">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
