<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useTranslation } from 'i18next-vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAccountStore } from '@/stores/account'
import { useChatStore } from '@/stores/chat'
import type { LlmSource, Provider } from '@/types/api'

/** Who pays for the answer: ShashGuru credits or the user's own API key. Hosted deployments only. */
const { t } = useTranslation()
const chat = useChatStore()
const account = useAccountStore()
const { prefs } = storeToRefs(chat)

const sources = computed<{ value: LlmSource; label: string }[]>(() => [
  { value: 'managed', label: t('chat.sourceManaged') },
  ...(account.byokEnabled ? [{ value: 'byok' as const, label: t('chat.sourceByok') }] : []),
])

const selectedKey = computed(() => account.keys.find((k) => k.id === prefs.value.keyId) ?? null)
const suggestions = computed(() => (selectedKey.value ? (account.models?.byok_suggestions[selectedKey.value.provider] ?? []) : []))

const keyLabel = (k: { label: string; provider: Provider; hint: string }) => `${k.label || t(`keys.providers.${k.provider}`)} …${k.hint}`

function setSource(value: unknown) {
  if (value === 'managed' || value === 'byok') prefs.value.source = value
}
function setModel(value: unknown) {
  if (typeof value === 'string') prefs.value.managedModel = value
}
function setKey(value: unknown) {
  const id = Number(value)
  if (Number.isInteger(id)) prefs.value.keyId = id
}
</script>

<template>
  <div class="llm-source flex flex-wrap items-end justify-center gap-3">
    <div class="flex flex-col gap-1.5">
      <Label for="source-selector" class="panel-label">{{ t('chat.source') }}</Label>
      <Select :model-value="prefs.source" @update:model-value="setSource">
        <SelectTrigger id="source-selector" class="w-44"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="s in sources" :key="s.value" :value="s.value">{{ s.label }}</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div v-if="prefs.source === 'managed' && account.models?.managed.length" class="flex flex-col gap-1.5">
      <Label for="model-selector" class="panel-label">{{ t('chat.model') }}</Label>
      <Select :model-value="prefs.managedModel" @update:model-value="setModel">
        <SelectTrigger id="model-selector" class="w-56"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="m in account.models.managed" :key="m.id" :value="m.id">
            {{ m.label }} · ~{{ m.est_credits }} {{ t('chat.creditsUnit') }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <template v-else-if="prefs.source === 'byok'">
      <div v-if="account.keys.length" class="flex flex-col gap-1.5">
        <Label for="key-selector" class="panel-label">{{ t('chat.key') }}</Label>
        <Select :model-value="String(prefs.keyId ?? '')" @update:model-value="setKey">
          <SelectTrigger id="key-selector" class="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem v-for="k in account.keys" :key="k.id" :value="String(k.id)">{{ keyLabel(k) }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div v-if="account.keys.length" class="flex flex-col gap-1.5">
        <Label for="byok-model" class="panel-label">{{ t('chat.model') }}</Label>
        <Input id="byok-model" v-model="prefs.byokModel" list="byok-models" class="w-56" :placeholder="t('chat.modelPlaceholder')" autocomplete="off" />
        <datalist id="byok-models"><option v-for="m in suggestions" :key="m" :value="m" /></datalist>
      </div>
      <p v-else class="text-sm text-warning">
        {{ t('chat.noKey') }}
        <RouterLink to="/account" class="underline">{{ t('chat.addKey') }}</RouterLink>
      </p>
    </template>
  </div>
</template>
