<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { Coins, Download, ExternalLink, Trash2 } from '@lucide/vue'
import ApiKeysManager from '@/components/ApiKeysManager.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { exportData } from '@/api/backend'
import { useAccountStore } from '@/stores/account'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const { t, i18next } = useTranslation()
const account = useAccountStore()
const auth = useAuthStore()
const toast = useToastStore()

const PAGE = 20
const portalBusy = ref(false)
const exporting = ref(false)
const loadingUsage = ref(false)
const confirmOpen = ref(false)
const confirmText = ref('')
const deleting = ref(false)

const me = computed(() => account.me)
const sub = computed(() => me.value?.subscription ?? null)
const num = (n: number) => new Intl.NumberFormat(i18next.language).format(n)
const date = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(i18next.language) : '—')
const dateTime = (iso: string) => new Date(iso).toLocaleString(i18next.language)
/** Typing the word protects against accidental clicks on an irreversible action. */
const confirmWord = computed(() => t('account.deleteWord'))
const canDelete = computed(() => confirmText.value.trim().toLowerCase() === confirmWord.value.toLowerCase() && !deleting.value)
const hasMore = computed(() => account.usage.items.length < account.usage.total)

const errorText = (e: unknown, fallback: string) => (e instanceof Error && e.message ? e.message : fallback)

async function loadMoreUsage(reset = false) {
  loadingUsage.value = true
  try {
    await account.loadUsage(PAGE, reset ? 0 : account.usage.items.length)
  } catch (e) {
    toast.error(errorText(e, t('account.loadFailed')))
  } finally {
    loadingUsage.value = false
  }
}

async function manageSubscription() {
  portalBusy.value = true
  try {
    await account.openPortal()
  } catch (e) {
    portalBusy.value = false
    toast.error(errorText(e, t('account.portalFailed')))
  }
}

async function downloadData() {
  exporting.value = true
  try {
    const blob = await exportData()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'shashguru-data.json'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(errorText(e, t('account.exportFailed')))
  } finally {
    exporting.value = false
  }
}

async function removeAccount() {
  if (!canDelete.value) return
  deleting.value = true
  try {
    await account.deleteAccount()
    confirmOpen.value = false
    toast.success(t('account.deleted'))
  } catch (e) {
    toast.error(errorText(e, t('account.deleteFailed')))
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await account.init()
  await Promise.all([account.refreshMe(), loadMoreUsage(true)])
})
</script>

<template>
  <main class="account mx-auto flex w-[calc(100%-2rem)] max-w-[900px] flex-col gap-6 py-10">
    <header class="space-y-1">
      <h1 class="text-3xl font-black tracking-wide text-lime">{{ t('account.title') }}</h1>
      <p class="text-muted-foreground">{{ auth.user?.email ?? me?.email }}</p>
    </header>

    <div v-if="!me" class="flex items-center gap-2 text-muted-foreground" role="status">
      <Spinner class="size-4" aria-hidden="true" />{{ t('account.loading') }}
    </div>

    <template v-else>
      <!-- Plan and balance -->
      <Card>
        <CardHeader>
          <CardTitle class="flex flex-wrap items-center gap-2">
            {{ t('account.plan') }}
            <Badge variant="secondary">{{ me.plan ?? t('account.planFree') }}</Badge>
            <Badge v-if="sub" variant="outline">{{ sub.status }}</Badge>
          </CardTitle>
          <CardDescription v-if="sub?.current_period_end">{{ t('account.renews', { date: date(sub.current_period_end) }) }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-3 sm:grid-cols-3">
            <div class="rounded-md border border-border p-3">
              <p class="panel-label">{{ t('account.creditsTotal') }}</p>
              <p class="num flex items-center gap-1.5 text-2xl font-bold text-lime"><Coins class="size-5" aria-hidden="true" />{{ num(me.balance.total) }}</p>
            </div>
            <div class="rounded-md border border-border p-3">
              <p class="panel-label">{{ t('account.creditsSubscription') }}</p>
              <p class="num text-xl font-semibold">{{ num(me.balance.subscription) }}</p>
            </div>
            <div class="rounded-md border border-border p-3">
              <p class="panel-label">{{ t('account.creditsPurchased') }}</p>
              <p class="num text-xl font-semibold">{{ num(me.balance.purchased) }}</p>
            </div>
          </div>
          <div v-if="account.billingEnabled" class="flex flex-wrap gap-2">
            <Button as-child><RouterLink to="/pricing">{{ t('account.buyCredits') }}</RouterLink></Button>
            <Button v-if="sub" variant="outline" :disabled="portalBusy" @click="manageSubscription">
              <Spinner v-if="portalBusy" class="size-4" aria-hidden="true" /><ExternalLink v-else aria-hidden="true" />{{ t('account.manageSubscription') }}
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- Usage this month -->
      <Card>
        <CardHeader><CardTitle>{{ t('account.usageMonth') }}</CardTitle></CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-4">
          <div><p class="panel-label">{{ t('account.requests') }}</p><p class="num text-lg font-semibold">{{ num(me.usage_month.requests) }}</p></div>
          <div><p class="panel-label">{{ t('account.inputTokens') }}</p><p class="num text-lg font-semibold">{{ num(me.usage_month.input_tokens) }}</p></div>
          <div><p class="panel-label">{{ t('account.outputTokens') }}</p><p class="num text-lg font-semibold">{{ num(me.usage_month.output_tokens) }}</p></div>
          <div><p class="panel-label">{{ t('account.creditsUsed') }}</p><p class="num text-lg font-semibold">{{ num(me.usage_month.credits) }}</p></div>
        </CardContent>
      </Card>

      <!-- API keys -->
      <Card v-if="account.byokEnabled">
        <CardHeader>
          <CardTitle>{{ t('keys.title') }}</CardTitle>
          <CardDescription>{{ t('keys.subtitle') }}</CardDescription>
        </CardHeader>
        <CardContent><ApiKeysManager /></CardContent>
      </Card>

      <!-- History -->
      <Card>
        <CardHeader><CardTitle>{{ t('account.history') }}</CardTitle></CardHeader>
        <CardContent class="space-y-3">
          <p v-if="account.usage.items.length === 0" class="text-sm text-muted-foreground">{{ t('account.historyEmpty') }}</p>
          <div v-else class="app-scrollbar overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs text-muted-foreground">
                <tr>
                  <th class="py-1.5 pr-3 font-medium">{{ t('account.colDate') }}</th>
                  <th class="py-1.5 pr-3 font-medium">{{ t('account.colSource') }}</th>
                  <th class="py-1.5 pr-3 font-medium">{{ t('account.colModel') }}</th>
                  <th class="py-1.5 pr-3 text-right font-medium">{{ t('account.colTokens') }}</th>
                  <th class="py-1.5 text-right font-medium">{{ t('account.colCredits') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in account.usage.items" :key="item.id" class="border-t border-border">
                  <td class="num py-1.5 pr-3 whitespace-nowrap">{{ dateTime(item.created_at) }}</td>
                  <td class="py-1.5 pr-3">{{ item.source === 'byok' ? t('chat.sourceByok') : t('chat.sourceManaged') }}</td>
                  <td class="py-1.5 pr-3">{{ item.model }}</td>
                  <td class="num py-1.5 pr-3 text-right">{{ num(item.input_tokens) }} / {{ num(item.output_tokens) }}</td>
                  <td class="num py-1.5 text-right">{{ item.source === 'byok' ? '—' : num(item.credits_charged) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <Button v-if="hasMore" variant="outline" size="sm" :disabled="loadingUsage" @click="loadMoreUsage()">
            <Spinner v-if="loadingUsage" class="size-3" aria-hidden="true" />{{ t('account.loadMore') }}
          </Button>
        </CardContent>
      </Card>

      <!-- Data and deletion -->
      <Card>
        <CardHeader>
          <CardTitle>{{ t('account.data') }}</CardTitle>
          <CardDescription>{{ t('account.dataText') }}</CardDescription>
        </CardHeader>
        <CardContent class="flex flex-wrap gap-2">
          <Button variant="outline" :disabled="exporting" @click="downloadData">
            <Spinner v-if="exporting" class="size-4" aria-hidden="true" /><Download v-else aria-hidden="true" />{{ t('account.export') }}
          </Button>
          <Button variant="destructive" @click="confirmOpen = true"><Trash2 aria-hidden="true" />{{ t('account.delete') }}</Button>
          <p class="w-full text-xs text-muted-foreground">
            <RouterLink to="/legal/terms" class="underline">{{ t('legal.termsTitle') }}</RouterLink> ·
            <RouterLink to="/legal/privacy" class="underline">{{ t('legal.privacyTitle') }}</RouterLink>
          </p>
        </CardContent>
      </Card>
    </template>

    <Dialog v-model:open="confirmOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('account.deleteTitle') }}</DialogTitle>
          <DialogDescription>{{ t('account.deleteText', { word: confirmWord }) }}</DialogDescription>
        </DialogHeader>
        <Input v-model="confirmText" :aria-label="t('account.deleteConfirmLabel')" :placeholder="confirmWord" autocomplete="off" />
        <DialogFooter>
          <Button variant="outline" @click="confirmOpen = false">{{ t('common.cancel') }}</Button>
          <Button variant="destructive" :disabled="!canDelete" @click="removeAccount">
            <Spinner v-if="deleting" class="size-4" aria-hidden="true" />{{ t('account.deleteConfirm') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </main>
</template>
