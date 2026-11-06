<script setup lang="ts">
import { useTranslation } from 'i18next-vue'
import ApiKeysManager from './ApiKeysManager.vue'
import EvaluationSettings from './EvaluationSettings.vue'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { useAccountStore } from '@/stores/account'
import { useAuthStore } from '@/stores/auth'

const { t } = useTranslation()
const account = useAccountStore()
const auth = useAuthStore()

defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="settings-modal max-h-[90dvh] overflow-y-auto sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ t('settings.title') }}</DialogTitle>
        <DialogDescription class="sr-only">{{ t('settings.description') }}</DialogDescription>
      </DialogHeader>
      <EvaluationSettings />
      <!-- Bring-your-own-key: hosted deployments only, for signed-in users -->
      <template v-if="account.byokEnabled && auth.signedIn">
        <Separator />
        <div class="space-y-3">
          <h3 class="panel-label text-foreground!">{{ t('keys.title') }}</h3>
          <ApiKeysManager />
        </div>
      </template>
    </DialogContent>
  </Dialog>
</template>
