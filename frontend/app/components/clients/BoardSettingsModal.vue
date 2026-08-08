<script setup lang="ts">
import { Bars3Icon, ExclamationTriangleIcon, PlusIcon, TrashIcon } from '@heroicons/vue/24/outline'
import draggable from 'vuedraggable'
import type { ApiError } from '~/composables/useApi'
import type { ClientStage } from '~/types/clients'
import type { ClientType } from '~/utils/clientStages'

const props = defineProps<{ clientType: ClientType }>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

const clientStageStore = useClientStageStore()

const orderedStages = reactive<ClientStage[]>([])

function syncOrderedStages(): void {
  const stagesForType = clientStageStore.stages
    .filter((stage) => stage.client_type === props.clientType)
    .sort((a, b) => a.order - b.order)
  // Splicing reads orderedStages.length, which — if this ran inside a
  // watchEffect — would make orderedStages itself an accidental dependency
  // of its own resync. vuedraggable mutates orderedStages directly on every
  // intermediate step of a drag; that would retrigger this function mid-drag
  // and immediately revert the live reorder back to the store's original
  // order, before the drop's @change handler ever sees the new order. Using
  // an explicit watch() (below) with a fixed source avoids that self-trigger.
  orderedStages.splice(0, Infinity, ...stagesForType)
}

watch(() => [clientStageStore.stages, props.clientType] as const, syncOrderedStages, { immediate: true })

// Decoupled from the store objects on purpose: binding the input directly to
// `stage.name` would mutate the shared ClientStage object (and therefore the
// live Kanban board) on every keystroke, before the rename is even saved.
const editedNames = reactive<Record<number, string>>({})

watchEffect(() => {
  for (const stage of orderedStages) {
    if (!(stage.id in editedNames)) {
      editedNames[stage.id] = stage.name
    }
  }
})

async function handleRename(stage: ClientStage): Promise<void> {
  const newName = editedNames[stage.id]?.trim()
  if (!newName || newName === stage.name) {
    editedNames[stage.id] = stage.name
    return
  }

  try {
    await clientStageStore.renameStage(stage.id, { name: newName })
  } catch {
    editedNames[stage.id] = stage.name
  }
}

async function handleReorder(): Promise<void> {
  try {
    await clientStageStore.reorderStages(orderedStages.map((stage) => stage.id))
  } catch {
    syncOrderedStages()
  }
}

const deleteErrorsByStageId = reactive<Record<number, string>>({})

async function handleDelete(stage: ClientStage): Promise<void> {
  delete deleteErrorsByStageId[stage.id]

  try {
    await clientStageStore.deleteStage(stage.id)
  } catch (e) {
    const apiError = e as ApiError
    deleteErrorsByStageId[stage.id] = apiError.statusCode === 409
      ? t('crm.clients.boardSettings.deleteConflict')
      : apiError.message
    // The per-row message above already surfaces this; avoid also showing
    // the raw (untranslated) backend text in the generic error alert below.
    clientStageStore.error = null
  }
}

const newStageName = ref('')

async function handleAddStage(): Promise<void> {
  const trimmedName = newStageName.value.trim()
  if (!trimmedName) {
    return
  }

  try {
    await clientStageStore.createStage({ client_type: props.clientType, name: trimmedName })
    newStageName.value = ''
  } catch {
    // ошибка уже сохранена в clientStageStore.error и показана ниже
  }
}
</script>

<template>
  <BaseModal :title="t('crm.clients.boardSettings.title')" @close="emit('close')">
    <div class="space-y-3">
      <draggable
        :list="orderedStages"
        handle=".drag-handle"
        item-key="id"
        class="space-y-2"
        ghost-class="opacity-40"
        @change="handleReorder"
      >
        <template #item="{ element: stage }">
          <div class="space-y-1">
            <div class="flex items-center gap-2 rounded-md border border-border bg-surface p-2">
              <span class="drag-handle cursor-grab text-muted-foreground">
                <Bars3Icon class="size-4" />
              </span>
              <input
                v-model="editedNames[stage.id]"
                type="text"
                class="flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-sm text-foreground focus:border-primary focus:bg-surface focus:outline-none focus:ring-1 focus:ring-primary"
                @blur="handleRename(stage)"
                @keydown.enter="($event.target as HTMLInputElement).blur()"
              >
              <button
                type="button"
                class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                :aria-label="t('common.buttons.delete')"
                @click="handleDelete(stage)"
              >
                <TrashIcon class="size-4" />
              </button>
            </div>
            <p v-if="deleteErrorsByStageId[stage.id]" class="flex items-center gap-1.5 px-1 text-xs text-destructive">
              <ExclamationTriangleIcon class="size-3.5 shrink-0" />
              {{ deleteErrorsByStageId[stage.id] }}
            </p>
          </div>
        </template>
      </draggable>

      <form class="flex items-center gap-2 border-t border-border pt-3" @submit.prevent="handleAddStage">
        <input
          v-model="newStageName"
          type="text"
          :placeholder="t('crm.clients.boardSettings.newStagePlaceholder')"
          class="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <button
          type="submit"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
        >
          <PlusIcon class="size-4" />
          {{ t('crm.clients.boardSettings.addStageButton') }}
        </button>
      </form>

      <div
        v-if="clientStageStore.error"
        class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <span>{{ clientStageStore.error }}</span>
      </div>
    </div>
  </BaseModal>
</template>
