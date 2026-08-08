<script setup lang="ts">
import type { EmployeeInvite } from '~/types/employeeInvites'

const props = defineProps<{ invite: EmployeeInvite }>()

const emit = defineEmits<{ close: [] }>()

const { t, d } = useI18n()

const formattedDate = (value: string): string => d(new Date(value), 'shortWithTime')
</script>

<template>
  <BaseModal :title="t(`crm.employees.invites.status.${invite.status}`)" @close="emit('close')">
    <dl class="space-y-3">
      <div v-if="invite.status === 'used' && invite.used_at">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.invites.usedAtLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ formattedDate(invite.used_at) }}</dd>
      </div>

      <template v-if="invite.status === 'revoked'">
        <div v-if="invite.cancellation_reason">
          <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.invites.cancellationReasonLabel') }}</dt>
          <dd class="mt-0.5 text-sm text-foreground">{{ invite.cancellation_reason }}</dd>
        </div>
        <p v-else class="text-sm text-muted-foreground">{{ t('crm.employees.invites.noCancellationReason') }}</p>
      </template>

      <div v-if="invite.status === 'expired'">
        <dt class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ t('crm.employees.invites.expiredAtLabel') }}</dt>
        <dd class="mt-0.5 text-sm text-foreground">{{ formattedDate(invite.expires_at) }}</dd>
      </div>
    </dl>
  </BaseModal>
</template>
