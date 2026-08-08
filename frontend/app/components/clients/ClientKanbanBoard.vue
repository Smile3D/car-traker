<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import draggable from 'vuedraggable'
import type { Client, ClientStage } from '~/types/clients'
import type { ClientType } from '~/utils/clientStages'
import { getClientStageColorClasses } from '~/utils/clientStageColors'
import { clientMatchesEmployeeFilter, type EmployeeFilterToken } from '~/utils/clientEmployeeFilter'

const props = defineProps<{ clientType: ClientType, employeeFilterTokens: EmployeeFilterToken[] }>()

const emit = defineEmits<{ select: [client: Client] }>()

const { t } = useI18n()

interface DraggableChangeEvent {
  added?: { element: Client, newIndex: number }
  removed?: { element: Client, oldIndex: number }
  moved?: { element: Client, newIndex: number, oldIndex: number }
}

const authStore = useAuthStore()
const { isEmployee } = useUserRole()
const clientStore = useClientStore()
const clientStageStore = useClientStageStore()
const listingStore = useListingStore()

const stages = computed<ClientStage[]>(() =>
  clientStageStore.stages
    .filter((stage) => stage.client_type === props.clientType)
    .sort((a, b) => a.order - b.order)
)

// A sold/removed listing's seller (or buyers) is no longer "in the works" —
// the Kanban board is a working view, so those cards drop out of it here.
// The List view intentionally keeps showing them (reference, not workflow),
// and nothing about the Client row itself changes — this is display-only.
const archivedListingIds = computed<Set<number>>(() =>
  new Set(
    listingStore.listings
      .filter((listing) => listing.status === 'sold' || listing.status === 'removed')
      .map((listing) => listing.id)
  )
)

const columns = reactive<Record<number, Client[]>>({})

function syncColumnsFromStore(): void {
  const clientsForType = clientStore.clients.filter((client) =>
    client.client_type === props.clientType
    && !archivedListingIds.value.has(client.listing_id)
    && clientMatchesEmployeeFilter(client, props.employeeFilterTokens, authStore.user?.id)
  )
  for (const stage of stages.value) {
    // vuedraggable's `:list` binding takes ownership of the array reference
    // it's given and mutates it directly during drag operations. Replacing
    // the reference here (e.g. `columns[stage.id] = [...]`) would desync
    // vuedraggable's internal state after any prior drag, causing cards to
    // disappear on the next unrelated store update. Mutate in place instead
    // so the array identity never changes.
    const clientsForStage = clientsForType.filter((client) => client.stage_id === stage.id)
    const columnArray = columns[stage.id] ?? (columns[stage.id] = [])
    // `.length` below reads the very array vuedraggable mutates mid-drag. If
    // this ran inside a watchEffect, that read would make columnArray an
    // accidental dependency of its own resync, retriggering (and reverting)
    // on every intermediate drag step. An explicit watch() (below) with a
    // fixed source avoids that self-trigger — see the same fix/explanation
    // in BoardSettingsModal.vue's syncOrderedStages.
    columnArray.splice(0, Infinity, ...clientsForStage)
  }
}

// deep: true is required here — the source getter only reads the
// clientStore.clients/listingStore.listings array REFERENCES, so without it
// Vue only reruns this on reassignment (e.g. fetchClients()'s
// `clients.value = [...]`), not on createClient's in-place `.push()`. That
// left newly created clients invisible on the board until a reload
// reassigned the array. Same fix as ListingPhotoGallery.vue's photo watcher.
watch(
  () => [clientStore.clients, stages.value, props.employeeFilterTokens, listingStore.listings] as const,
  syncColumnsFromStore,
  { immediate: true, deep: true }
)

const dragError = ref<string | null>(null)

// Mirrors the backend rule in listing_authorization.py: only the "seller"
// board represents lots — the "buyer" board is a different relationship
// and isn't restricted here. Unassigned/self-assigned stays draggable.
function isSellerLockedForCurrentEmployee(client: Client): boolean {
  return (
    props.clientType === 'seller'
    && isEmployee.value
    && client.employee_id !== null
    && client.employee_id !== authStore.user.id
  )
}

function handleMove(evt: { draggedContext: { element: Client } }): boolean {
  if (isSellerLockedForCurrentEmployee(evt.draggedContext.element)) {
    dragError.value = t('listingDetails.foreignListingNotice')
    return false
  }
  return true
}

async function handleColumnChange(stageId: number, changeEvent: DraggableChangeEvent): Promise<void> {
  if (!changeEvent.added) {
    return
  }

  const movedClient = changeEvent.added.element
  dragError.value = null

  try {
    await clientStore.updateClient(movedClient.id, { stage_id: stageId })
  } catch {
    dragError.value = clientStore.error
    syncColumnsFromStore()
  }
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="dragError" class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive" role="alert">
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ dragError }}</span>
    </div>

    <div class="grid grid-flow-col auto-cols-[16rem] gap-4 overflow-x-auto pb-2">
      <div
        v-for="stage in stages"
        :key="stage.id"
        class="flex flex-col rounded-lg border border-border bg-muted/30 p-3"
      >
        <h3 class="mb-3 flex items-center justify-between gap-2 text-xs font-semibold uppercase tracking-wide">
          <span class="truncate rounded-md px-2 py-0.5" :class="getClientStageColorClasses(stage.order)">{{ stage.name }}</span>
          <span class="shrink-0 tabular-nums text-muted-foreground">{{ columns[stage.id]?.length ?? 0 }}</span>
        </h3>

        <draggable
          :list="columns[stage.id]"
          group="clients-board"
          item-key="id"
          class="flex min-h-[4rem] flex-1 flex-col gap-2"
          ghost-class="opacity-40"
          :move="handleMove"
          @change="handleColumnChange(stage.id, $event)"
        >
          <template #item="{ element }">
            <ClientCard :client="element" @click="emit('select', element)" />
          </template>
        </draggable>
      </div>
    </div>
  </div>
</template>
