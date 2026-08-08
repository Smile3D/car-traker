<script setup lang="ts">
import { ExclamationTriangleIcon, PlusIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type { ApiError } from '~/composables/useApi'
import type { Position } from '~/types/positions'

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

const positionStore = usePositionStore()

// Decoupled from the store objects on purpose: binding the input directly to
// `position.name` would mutate the shared Position object on every
// keystroke, before the rename is even saved.
const editedNames = reactive<Record<number, string>>({})

watchEffect(() => {
  for (const position of positionStore.positions) {
    if (!(position.id in editedNames)) {
      editedNames[position.id] = position.name
    }
  }
})

async function handleRename(position: Position): Promise<void> {
  const newName = editedNames[position.id]?.trim()
  if (!newName || newName === position.name) {
    editedNames[position.id] = position.name
    return
  }

  try {
    await positionStore.renamePosition(position.id, { name: newName })
  } catch {
    editedNames[position.id] = position.name
  }
}

const deleteErrorsByPositionId = reactive<Record<number, string>>({})

async function handleDelete(position: Position): Promise<void> {
  delete deleteErrorsByPositionId[position.id]

  try {
    await positionStore.deletePosition(position.id)
  } catch (e) {
    const apiError = e as ApiError
    deleteErrorsByPositionId[position.id] = apiError.statusCode === 409
      ? t('crm.employees.positions.deleteConflict')
      : apiError.message
    // The per-row message above already surfaces this; avoid also showing
    // the raw (untranslated) backend text in the generic error alert below.
    positionStore.error = null
  }
}

const newPositionName = ref('')

async function handleAddPosition(): Promise<void> {
  const trimmedName = newPositionName.value.trim()
  if (!trimmedName) {
    return
  }

  try {
    await positionStore.createPosition({ name: trimmedName })
    newPositionName.value = ''
  } catch {
    // ошибка уже сохранена в positionStore.error и показана ниже
  }
}
</script>

<template>
  <BaseModal :title="t('crm.employees.positions.title')" @close="emit('close')">
    <div class="space-y-3">
      <div v-if="positionStore.positions.length === 0" class="py-4 text-center text-sm text-muted-foreground">
        {{ t('crm.employees.positions.empty') }}
      </div>

      <div v-for="position in positionStore.positions" :key="position.id" class="space-y-1">
        <div class="flex items-center gap-2 rounded-md border border-border bg-surface p-2">
          <input
            v-model="editedNames[position.id]"
            type="text"
            class="flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-sm text-foreground focus:border-primary focus:bg-surface focus:outline-none focus:ring-1 focus:ring-primary"
            @blur="handleRename(position)"
            @keydown.enter="($event.target as HTMLInputElement).blur()"
          >
          <button
            type="button"
            class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            :aria-label="t('common.buttons.delete')"
            @click="handleDelete(position)"
          >
            <TrashIcon class="size-4" />
          </button>
        </div>
        <p v-if="deleteErrorsByPositionId[position.id]" class="flex items-center gap-1.5 px-1 text-xs text-destructive">
          <ExclamationTriangleIcon class="size-3.5 shrink-0" />
          {{ deleteErrorsByPositionId[position.id] }}
        </p>
      </div>

      <form class="flex items-center gap-2 border-t border-border pt-3" @submit.prevent="handleAddPosition">
        <input
          v-model="newPositionName"
          type="text"
          :placeholder="t('crm.employees.positions.newPositionPlaceholder')"
          class="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <button
          type="submit"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        >
          <PlusIcon class="size-4" />
          {{ t('crm.employees.positions.addButton') }}
        </button>
      </form>

      <div
        v-if="positionStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ positionStore.error }}</span>
      </div>
    </div>
  </BaseModal>
</template>
