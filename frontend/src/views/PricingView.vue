<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { Check, Coins, KeyRound, Sparkles } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { useAccountStore } from '@/stores/account'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Offer } from '@/types/api'

const { t, i18next } = useTranslation()
const route = useRoute()
const account = useAccountStore()
const auth = useAuthStore()
const toast = useToastStore()

const busy = ref<string | null>(null)

const subscriptions = computed(() => account.offers.filter((o) => o.kind === 'subscription'))
const topups = computed(() => account.offers.filter((o) => o.kind === 'topup'))

function price(offer: Offer): string {
  try {
    return new Intl.NumberFormat(i18next.language, { style: 'currency', currency: offer.currency.toUpperCase() }).format(offer.price)
  } catch {
    return `${offer.price} ${offer.currency}`
  }
}

async function buy(offer: Offer) {
  if (!auth.signedIn) {
    await auth.signIn()
    return
  }
  busy.value = offer.id
  try {
    await account.checkout(offer.id)
  } catch (e) {
    busy.value = null
    toast.error(e instanceof Error && e.message ? e.message : t('pricing.checkoutFailed'))
  }
}

onMounted(async () => {
  await account.init()
  if (account.billingEnabled && account.offers.length === 0) await account.loadOffers()
  // The payment provider sends the user back here with ?checkout=success|cancelled
  if (route.query.checkout === 'success') {
    toast.success(t('pricing.paymentSuccess'))
    if (auth.signedIn) await account.refreshMe()
  } else if (route.query.checkout === 'cancelled') {
    toast.info(t('pricing.paymentCancelled'))
  }
})
</script>

<template>
  <main class="pricing mx-auto flex w-[calc(100%-2rem)] max-w-[1100px] flex-col gap-8 py-10">
    <header class="space-y-2 text-center">
      <h1 class="text-3xl font-black tracking-wide text-lime">{{ t('pricing.title') }}</h1>
      <p class="mx-auto max-w-[60ch] text-muted-foreground">{{ t('pricing.subtitle') }}</p>
    </header>

    <!-- Free + BYOK -->
    <section class="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2"><Sparkles class="size-5 text-lime" aria-hidden="true" />{{ t('pricing.free.title') }}</CardTitle>
          <CardDescription>{{ t('pricing.free.text') }}</CardDescription>
        </CardHeader>
        <CardContent>
          <ul class="space-y-1.5 text-sm">
            <li class="flex gap-2"><Check class="size-4 shrink-0 text-success" aria-hidden="true" />{{ t('pricing.free.engine') }}</li>
            <li class="flex gap-2"><Check class="size-4 shrink-0 text-success" aria-hidden="true" />{{ t('pricing.free.board') }}</li>
          </ul>
        </CardContent>
      </Card>
      <Card v-if="account.byokEnabled">
        <CardHeader>
          <CardTitle class="flex items-center gap-2"><KeyRound class="size-5 text-lime" aria-hidden="true" />{{ t('pricing.byok.title') }}</CardTitle>
          <CardDescription>{{ t('pricing.byok.text') }}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" as-child><RouterLink to="/account">{{ t('pricing.byok.cta') }}</RouterLink></Button>
        </CardContent>
      </Card>
    </section>

    <!-- Subscriptions -->
    <section v-if="subscriptions.length" class="space-y-3">
      <h2 class="panel-label text-foreground!">{{ t('pricing.subscriptions') }}</h2>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card v-for="offer in subscriptions" :key="offer.id" class="flex flex-col">
          <CardHeader>
            <CardTitle class="flex items-center justify-between gap-2">
              {{ offer.name }}
              <Badge v-if="account.me?.subscription?.offer_id === offer.id" variant="secondary">{{ t('pricing.current') }}</Badge>
            </CardTitle>
            <CardDescription>
              <span class="num text-2xl font-bold text-foreground">{{ price(offer) }}</span> / {{ t('pricing.month') }}
            </CardDescription>
          </CardHeader>
          <CardContent class="mt-auto space-y-3">
            <p class="num flex items-center gap-1.5 text-sm"><Coins class="size-4 text-lime" aria-hidden="true" />{{ t('pricing.creditsPerMonth', { count: offer.credits }) }}</p>
            <Button class="w-full" :disabled="busy !== null" @click="buy(offer)">
              <Spinner v-if="busy === offer.id" class="size-4" aria-hidden="true" />{{ auth.signedIn ? t('pricing.subscribe') : t('auth.signInToContinue') }}
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- Top-ups -->
    <section v-if="topups.length" class="space-y-3">
      <h2 class="panel-label text-foreground!">{{ t('pricing.topups') }}</h2>
      <p class="text-sm text-muted-foreground">{{ t('pricing.topupsText') }}</p>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card v-for="offer in topups" :key="offer.id" class="flex flex-col">
          <CardHeader>
            <CardTitle>{{ offer.name }}</CardTitle>
            <CardDescription><span class="num text-2xl font-bold text-foreground">{{ price(offer) }}</span></CardDescription>
          </CardHeader>
          <CardContent class="mt-auto space-y-3">
            <p class="num flex items-center gap-1.5 text-sm"><Coins class="size-4 text-lime" aria-hidden="true" />{{ t('pricing.credits', { count: offer.credits }) }}</p>
            <Button variant="outline" class="w-full" :disabled="busy !== null" @click="buy(offer)">
              <Spinner v-if="busy === offer.id" class="size-4" aria-hidden="true" />{{ auth.signedIn ? t('pricing.buy') : t('auth.signInToContinue') }}
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>

    <p class="text-center text-xs text-muted-foreground">
      {{ t('pricing.footnote') }}
      <RouterLink to="/legal/terms" class="underline">{{ t('legal.termsTitle') }}</RouterLink> ·
      <RouterLink to="/legal/privacy" class="underline">{{ t('legal.privacyTitle') }}</RouterLink>
    </p>
  </main>
</template>
