<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import { CircleUser, Coins, LogOut, Settings2, Tag } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAccountStore } from '@/stores/account'
import { useAuthStore } from '@/stores/auth'

/** Login / account entry of the header. Renders nothing unless this is a hosted deployment with a login provider. */
defineProps<{ mobile?: boolean }>()

const { t } = useTranslation()
const auth = useAuthStore()
const account = useAccountStore()

const label = computed(() => auth.user?.name || auth.user?.email || t('auth.account'))
const credits = computed(() => account.balance?.total ?? null)
</script>

<template>
  <div v-if="account.saas" class="account-menu" :class="mobile ? 'flex flex-col gap-1' : 'flex items-center gap-2'">
    <template v-if="!auth.signedIn">
      <Button variant="ghost" size="sm" :class="mobile ? 'justify-start' : ''" @click="auth.signIn()">{{ t('auth.signIn') }}</Button>
      <Button size="sm" :class="mobile ? 'justify-start' : ''" @click="auth.signUp()">{{ t('auth.signUp') }}</Button>
    </template>

    <template v-else-if="mobile">
      <RouterLink
        v-if="account.billingEnabled"
        to="/pricing"
        class="flex items-center gap-2 rounded-md px-3 py-3 text-base font-semibold text-cream/85 hover:bg-accent"
      >
        <Tag class="size-4" aria-hidden="true" />{{ t('nav.pricing') }}
      </RouterLink>
      <RouterLink to="/account" class="flex items-center gap-2 rounded-md px-3 py-3 text-base font-semibold text-cream/85 hover:bg-accent">
        <CircleUser class="size-4" aria-hidden="true" />{{ label }}
        <Badge v-if="credits !== null" variant="outline" class="num ml-auto gap-1"><Coins aria-hidden="true" />{{ credits }}</Badge>
      </RouterLink>
      <Button variant="ghost" class="justify-start" @click="auth.signOut()"><LogOut aria-hidden="true" />{{ t('auth.signOut') }}</Button>
    </template>

    <template v-else>
      <RouterLink v-if="credits !== null" to="/account" class="hidden lg:block" :title="t('auth.creditsTitle')">
        <Badge variant="outline" class="num gap-1 text-lime"><Coins aria-hidden="true" />{{ t('auth.credits', { count: credits }) }}</Badge>
      </RouterLink>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="sm" class="max-w-44 gap-1.5" :aria-label="t('auth.account')">
            <CircleUser aria-hidden="true" /><span class="truncate">{{ label }}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-56">
          <DropdownMenuLabel class="truncate">{{ auth.user?.email ?? label }}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem as-child>
            <RouterLink to="/account"><Settings2 aria-hidden="true" />{{ t('auth.account') }}</RouterLink>
          </DropdownMenuItem>
          <DropdownMenuItem v-if="account.billingEnabled" as-child>
            <RouterLink to="/pricing"><Tag aria-hidden="true" />{{ t('nav.pricing') }}</RouterLink>
          </DropdownMenuItem>
          <DropdownMenuItem v-if="auth.canOpenAccount" @select="auth.openAccount()">
            <CircleUser aria-hidden="true" />{{ t('auth.manageLogin') }}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem @select="auth.signOut()"><LogOut aria-hidden="true" />{{ t('auth.signOut') }}</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </template>
  </div>
</template>
