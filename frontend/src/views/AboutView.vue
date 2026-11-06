<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { useAccountStore } from '@/stores/account'

const { t } = useTranslation()
const account = useAccountStore()
</script>

<template>
  <main class="about mx-auto flex max-w-[70ch] flex-col gap-(--gap) px-4 py-12 md:min-h-[calc(100dvh-var(--navbar-h))] md:justify-center">
    <div class="flex items-center gap-3">
      <img src="/pawn-logo.svg" alt="" class="size-10" />
      <span class="text-3xl font-black tracking-[0.06em] text-lime">ShashGuru</span>
    </div>

    <!-- Translations are our own static strings containing only <strong>/<em> -->
    <p class="md-content text-xl leading-relaxed text-foreground" v-html="t('about.intro')"></p>
    <p class="num text-sm text-muted-foreground">{{ t('about.copyright') }}</p>

    <section class="panel space-y-4 p-(--pad) text-[15px] leading-relaxed text-muted-foreground">
      <p class="md-content" v-html="t('about.license')"></p>
      <p class="md-content" v-html="t('about.warranty')"></p>
      <p class="md-content">
        {{ t('about.copy') }}
        <a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank" rel="noopener noreferrer"
          >www.gnu.org/licenses</a
        >.
      </p>
      <p class="md-content">
        <a href="https://github.com/Bosslibra/ShashGuru" target="_blank" rel="noopener noreferrer">{{ t('about.source') }}</a>
        · {{ t('about.engines') }}
      </p>
      <p v-if="account.saas" class="md-content">
        <RouterLink to="/legal/terms">{{ t('legal.termsTitle') }}</RouterLink> ·
        <RouterLink to="/legal/privacy">{{ t('legal.privacyTitle') }}</RouterLink>
      </p>
    </section>
  </main>
</template>
