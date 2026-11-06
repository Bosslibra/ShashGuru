<script setup lang="ts">
import { defineAsyncComponent, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { Languages, Menu } from '@lucide/vue'
import { SUPPORTED_LANGUAGES } from '@/i18n'
import { Toaster } from '@/components/ui/sonner'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { TooltipProvider } from '@/components/ui/tooltip'

const { t, i18next } = useTranslation()
const route = useRoute()

// Visual-direction switcher: DEV only (the dead branch is removed from the production build)
const DevDirectionSwitcher = import.meta.env.DEV
  ? defineAsyncComponent(() => import('@/dev/DevDirectionSwitcher.vue'))
  : null

const NAV = [
  { to: '/', key: 'nav.home' },
  { to: '/live', key: 'nav.live' },
  { to: '/about', key: 'nav.about' },
] as const

const menuOpen = ref(false)
watch(
  () => route.fullPath,
  () => (menuOpen.value = false),
)

function currentLanguage(): string {
  return (i18next.resolvedLanguage || i18next.language || 'en').split('-')[0]
}

const language = ref(currentLanguage())
const onLanguageChanged = () => (language.value = currentLanguage())
i18next.on('languageChanged', onLanguageChanged)
onUnmounted(() => i18next.off('languageChanged', onLanguageChanged))

function changeLanguage(value: unknown) {
  if (typeof value === 'string') i18next.changeLanguage(value)
}
</script>

<template>
  <TooltipProvider :delay-duration="300">
  <header class="sticky top-0 z-40 border-b border-olive/70 bg-surface-nav/95 backdrop-blur">
    <nav class="mx-auto flex h-16 max-w-[1800px] items-center gap-2 px-4 md:px-6">
      <RouterLink
        to="/"
        class="group flex items-center gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <img src="/pawn-logo.svg" alt="" class="size-7 shrink-0" />
        <span class="text-xl font-black tracking-[0.06em] text-lime md:text-2xl">ShashGuru</span>
      </RouterLink>

      <!-- Desktop links -->
      <div class="ml-4 hidden items-center gap-1 md:flex">
        <RouterLink
          v-for="item in NAV"
          :key="item.to"
          :to="item.to"
          data-slot="nav-link"
          class="relative rounded-md px-3 py-2 text-sm font-semibold tracking-wider text-cream/80 outline-none transition-colors hover:text-lime focus-visible:ring-2 focus-visible:ring-ring aria-[current=page]:text-lime"
        >
          {{ t(item.key) }}
        </RouterLink>
      </div>

      <!-- Desktop language -->
      <div class="ml-auto hidden items-center gap-2 md:flex">
        <Languages class="size-4 text-cream/70" aria-hidden="true" />
        <Select :model-value="language" @update:model-value="changeLanguage">
          <SelectTrigger size="sm" class="w-[72px]" :aria-label="t('nav.language')">
            <SelectValue />
          </SelectTrigger>
          <SelectContent align="end">
            <SelectItem v-for="lng in SUPPORTED_LANGUAGES" :key="lng" :value="lng">
              {{ lng.toUpperCase() }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <!-- Mobile menu -->
      <div class="ml-auto md:hidden">
        <Sheet v-model:open="menuOpen">
          <SheetTrigger as-child>
            <Button variant="ghost" size="icon" :aria-label="t('nav.toggle')">
              <Menu aria-hidden="true" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" class="w-72 p-4">
            <SheetTitle class="sr-only">{{ t('nav.toggle') }}</SheetTitle>
            <SheetDescription class="sr-only">{{ t('nav.language') }}</SheetDescription>
            <div class="mt-8 flex flex-col gap-1">
              <RouterLink
                v-for="item in NAV"
                :key="item.to"
                :to="item.to"
                data-slot="nav-link"
                class="rounded-md px-3 py-3 text-base font-semibold tracking-wider text-cream/85 outline-none transition-colors hover:bg-accent aria-[current=page]:text-lime"
              >
                {{ t(item.key) }}
              </RouterLink>
            </div>
            <div class="mt-4 flex items-center gap-2 border-t border-border pt-4">
              <Languages class="size-4 text-muted-foreground" aria-hidden="true" />
              <Select :model-value="language" @update:model-value="changeLanguage">
                <SelectTrigger class="w-24" :aria-label="t('nav.language')">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="lng in SUPPORTED_LANGUAGES" :key="lng" :value="lng">
                    {{ lng.toUpperCase() }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  </header>

  <RouterView />
  <Toaster position="bottom-right" />
  <component :is="DevDirectionSwitcher" v-if="DevDirectionSwitcher" />
  </TooltipProvider>
</template>
