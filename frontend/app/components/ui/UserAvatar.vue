<script setup lang="ts">
const props = withDefaults(defineProps<{ sizeClass?: string }>(), {
  sizeClass: 'size-8 text-sm',
})

const authStore = useAuthStore()

const avatarImageUrl = ref<string | null>(null)

const userInitial = computed<string>(() => authStore.user?.email?.charAt(0).toUpperCase() ?? '?')

function revokeAvatarImageUrl(): void {
  if (avatarImageUrl.value) {
    URL.revokeObjectURL(avatarImageUrl.value)
    avatarImageUrl.value = null
  }
}

async function loadAvatarImageUrl(): Promise<void> {
  revokeAvatarImageUrl()

  if (!authStore.user?.avatar_url) {
    return
  }

  try {
    avatarImageUrl.value = await authStore.fetchAvatarImageUrl()
  } catch {
    avatarImageUrl.value = null
  }
}

watch(() => authStore.user?.avatar_url, loadAvatarImageUrl, { immediate: true })

onUnmounted(() => {
  revokeAvatarImageUrl()
})
</script>

<template>
  <img
    v-if="avatarImageUrl"
    :src="avatarImageUrl"
    :class="props.sizeClass"
    class="rounded-full object-cover"
    alt=""
  >
  <span
    v-else
    :class="props.sizeClass"
    class="flex items-center justify-center rounded-full bg-muted font-semibold text-foreground"
  >
    {{ userInitial }}
  </span>
</template>
