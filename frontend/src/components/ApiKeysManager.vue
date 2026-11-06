<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { CircleCheck, CircleX, KeyRound, Plus, Trash2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useAccountStore } from '@/stores/account'
import { useToastStore } from '@/stores/toast'
import { PROVIDERS, type Provider } from '@/types/api'

const { t } = useTranslation()
const account = useAccountStore()
const toast = useToastStore()

const provider = ref<Provider>('openai')
const apiKey = ref('')
const label = ref('')
const baseUrl = ref('')
const saving = ref(false)
const testing = ref<number | null>(null)
const testResult = ref<Record<number, { ok: boolean; message?: string }>>({})

const needsBaseUrl = computed(() => provider.value === 'custom')
const canSave = computed(() => !!apiKey.value.trim() && (!needsBaseUrl.value || !!baseUrl.value.trim()) && !saving.value)

function errorText(e: unknown): string {
  return e instanceof Error && e.message ? e.message : t('keys.failed')
}

function onProviderChange(value: unknown) {
  if (typeof value === 'string') provider.value = value as Provider
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  try {
    await account.addKey({
      provider: provider.value,
      api_key: apiKey.value.trim(),
      label: label.value.trim() || undefined,
      base_url: needsBaseUrl.value ? baseUrl.value.trim() : undefined,
    })
    apiKey.value = ''
    label.value = ''
    baseUrl.value = ''
    toast.success(t('keys.saved'))
  } catch (e) {
    toast.error(errorText(e))
  } finally {
    saving.value = false
  }
}

async function test(id: number) {
  testing.value = id
  try {
    testResult.value[id] = await account.testKey(id)
  } catch (e) {
    testResult.value[id] = { ok: false, message: errorText(e) }
  } finally {
    testing.value = null
  }
}

async function remove(id: number) {
  try {
    await account.removeKey(id)
  } catch (e) {
    toast.error(errorText(e))
  }
}

const formatDate = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString() : t('keys.never'))
</script>

<template>
  <section class="api-keys space-y-4">
    <p class="text-sm text-muted-foreground">{{ t('keys.intro') }}</p>

    <ul v-if="account.keys.length" class="space-y-2">
      <li v-for="key in account.keys" :key="key.id" class="rounded-md border border-border p-3">
        <div class="flex flex-wrap items-center gap-2">
          <KeyRound class="size-4 text-lime" aria-hidden="true" />
          <span class="font-semibold">{{ key.label || t(`keys.providers.${key.provider}`) }}</span>
          <Badge variant="outline">{{ t(`keys.providers.${key.provider}`) }}</Badge>
          <span class="num text-sm text-muted-foreground">…{{ key.hint }}</span>
          <div class="ml-auto flex items-center gap-1">
            <Button variant="outline" size="sm" :disabled="testing === key.id" @click="test(key.id)">
              <Spinner v-if="testing === key.id" class="size-3" aria-hidden="true" />{{ t('keys.test') }}
            </Button>
            <Button variant="ghost" size="icon-sm" :aria-label="t('keys.delete')" @click="remove(key.id)">
              <Trash2 aria-hidden="true" />
            </Button>
          </div>
        </div>
        <p class="mt-1 text-xs text-muted-foreground">
          <span v-if="key.base_url" class="break-all">{{ key.base_url }} · </span>{{ t('keys.lastUsed', { date: formatDate(key.last_used_at) }) }}
        </p>
        <p
          v-if="testResult[key.id]"
          class="mt-1 flex items-center gap-1 text-xs"
          :class="testResult[key.id].ok ? 'text-success' : 'text-destructive'"
          role="status"
        >
          <component :is="testResult[key.id].ok ? CircleCheck : CircleX" class="size-3.5" aria-hidden="true" />
          {{ testResult[key.id].ok ? t('keys.testOk') : testResult[key.id].message || t('keys.testFailed') }}
        </p>
      </li>
    </ul>
    <p v-else class="text-sm text-muted-foreground">{{ t('keys.empty') }}</p>

    <form class="space-y-3 rounded-md border border-dashed border-border p-3" @submit.prevent="save">
      <h4 class="panel-label">{{ t('keys.add') }}</h4>
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="flex flex-col gap-1.5">
          <Label for="key-provider">{{ t('keys.provider') }}</Label>
          <Select :model-value="provider" @update:model-value="onProviderChange">
            <SelectTrigger id="key-provider"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="p in PROVIDERS" :key="p" :value="p">{{ t(`keys.providers.${p}`) }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex flex-col gap-1.5">
          <Label for="key-label">{{ t('keys.label') }}</Label>
          <Input id="key-label" v-model="label" :placeholder="t('keys.labelPlaceholder')" autocomplete="off" />
        </div>
      </div>
      <div v-if="needsBaseUrl" class="flex flex-col gap-1.5">
        <Label for="key-base-url">{{ t('keys.baseUrl') }}</Label>
        <Input id="key-base-url" v-model="baseUrl" type="url" placeholder="https://api.example.com/v1" autocomplete="off" />
        <p class="text-xs text-muted-foreground">{{ t('keys.baseUrlHint') }}</p>
      </div>
      <div class="flex flex-col gap-1.5">
        <Label for="key-secret">{{ t('keys.apiKey') }}</Label>
        <Input id="key-secret" v-model="apiKey" type="password" autocomplete="off" spellcheck="false" placeholder="sk-…" />
      </div>
      <p class="text-xs text-muted-foreground">{{ t('keys.storedEncrypted') }}</p>
      <Button type="submit" :disabled="!canSave">
        <Spinner v-if="saving" class="size-3" aria-hidden="true" /><Plus v-else aria-hidden="true" />{{ t('keys.save') }}
      </Button>
    </form>
  </section>
</template>
