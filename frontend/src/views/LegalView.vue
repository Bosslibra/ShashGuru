<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { TriangleAlert } from '@lucide/vue'

/** Terms of Service / Privacy Policy, rendered from the translations. The text is a draft for legal review. */
const { t } = useTranslation()
const route = useRoute()

const doc = computed<'terms' | 'privacy'>(() => (route.meta.doc === 'privacy' ? 'privacy' : 'terms'))
const title = computed(() => (doc.value === 'privacy' ? t('legal.privacyTitle') : t('legal.termsTitle')))
const sections = computed(
  () => t(`legal.${doc.value}.sections`, { returnObjects: true }) as unknown as { title: string; body: string }[],
)
// Bump when the text changes materially.
const UPDATED = '2026-11-06'
</script>

<template>
  <main class="legal mx-auto flex w-[calc(100%-2rem)] max-w-[75ch] flex-col gap-6 py-10">
    <h1 class="text-3xl font-black tracking-wide text-lime">{{ title }}</h1>
    <Alert>
      <TriangleAlert aria-hidden="true" />
      <AlertDescription>{{ t('legal.draft') }}</AlertDescription>
    </Alert>
    <p class="num text-sm text-muted-foreground">{{ t('legal.updated', { date: UPDATED }) }}</p>
    <section v-for="section in sections" :key="section.title" class="space-y-1.5">
      <h2 class="text-lg font-semibold">{{ section.title }}</h2>
      <p class="leading-relaxed text-muted-foreground">{{ section.body }}</p>
    </section>
    <RouterLink to="/" class="text-sm text-lime underline">{{ t('legal.back') }}</RouterLink>
  </main>
</template>
