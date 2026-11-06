<script setup lang="ts">
import { useTranslation } from 'i18next-vue'
import EvaluationSettings from './EvaluationSettings.vue'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const { t } = useTranslation()

defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="settings-modal sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ t('settings.title') }}</DialogTitle>
        <DialogDescription class="sr-only">{{ t('settings.description') }}</DialogDescription>
      </DialogHeader>
      <EvaluationSettings />
    </DialogContent>
  </Dialog>
</template>
