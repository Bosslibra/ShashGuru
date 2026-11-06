<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { CircleAlert, Search } from '@lucide/vue'
import EventSection from '@/components/EventSection.vue'
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from '@/components/ui/input-group'
import { Spinner } from '@/components/ui/spinner'
import { fetchRoundPgn } from '@/api/lichess'
import { parseBroadcastInput, parseHeaders, splitPgns } from '@/lib/pgn'

const { t } = useTranslation()

// Lichess broadcast round shown as "Featured Event" (a test round; empty it in production)
const featuredEvent = ref(import.meta.env.VITE_FEATURED_EVENT_ID || 'bFcndX91')

const roundId = ref('')
const pgnListFeatured = ref<string[]>([])
const pgnListAsked = ref<string[]>([])
const loadingFeatured = ref(false)
const loadingQueried = ref(false)
const loadedFeatured = ref(false)
const loadedQueried = ref(false)
const error = ref<string | null>(null)
const searchHasHappened = ref(false)
const searchInput = ref('')

const loading = computed(() => loadingFeatured.value || loadingQueried.value)

/** Games of a round, or null (and `error` set) if they could not be fetched. */
async function loadRound(id: string): Promise<string[] | null> {
  error.value = null
  try {
    return splitPgns(await fetchRoundPgn(id))
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('errors.fetchPgn')
    return null
  }
}

async function refreshQueriedEvent() {
  if (!roundId.value) return
  loadingQueried.value = true
  const games = await loadRound(roundId.value)
  if (games) pgnListAsked.value = games
  loadingQueried.value = false
  loadedQueried.value = true
}

async function fetchQueriedPgn() {
  const parsed = parseBroadcastInput(searchInput.value)
  if (!parsed) {
    error.value = t('errors.invalidBroadcast')
    return
  }
  roundId.value = parsed.roundId
  searchHasHappened.value = true
  await refreshQueriedEvent()
}

async function refreshFeaturedEvent() {
  if (!featuredEvent.value) return
  loadingFeatured.value = true
  const games = await loadRound(featuredEvent.value)
  if (games) pgnListFeatured.value = games
  loadingFeatured.value = false
  loadedFeatured.value = true
}

function eventTitle(games: string[], loaded: boolean): string {
  if (!games.length) return loaded ? t('live.unavailable') : t('live.loadingTitle')
  return parseHeaders(games[0]).Event || t('live.unknownEvent')
}

const featuredEventTitle = computed(() => eventTitle(pgnListFeatured.value, loadedFeatured.value))
const queriedEventTitle = computed(() => eventTitle(pgnListAsked.value, loadedQueried.value))

onMounted(refreshFeaturedEvent)
</script>

<template>
  <main class="mx-auto flex w-[calc(100%-2rem)] max-w-[1400px] flex-col gap-(--gap) py-(--pad)">
    <!-- Search -->
    <section>
      <h2 class="mb-5 text-center text-2xl font-bold text-foreground md:text-3xl">{{ t('live.title') }}</h2>

      <InputGroup id="search-group" class="h-11 rounded-full border-olive/70">
        <InputGroupAddon>
          <Search class="ml-1" aria-hidden="true" />
        </InputGroupAddon>
        <InputGroupInput
          id="input-event"
          v-model="searchInput"
          :placeholder="t('live.searchPlaceholder')"
          :aria-label="t('live.searchLabel')"
          autocomplete="off"
          @keyup.enter="fetchQueriedPgn"
        />
        <InputGroupAddon align="inline-end">
          <InputGroupButton
            id="search-button"
            variant="default"
            size="sm"
            class="rounded-full"
            :disabled="loading"
            :aria-label="t('live.search')"
            @click="fetchQueriedPgn"
          >
            <Spinner v-if="loading" aria-hidden="true" />
            <Search v-else aria-hidden="true" />
            <span class="hidden sm:inline">{{ t('live.search') }}</span>
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>

      <p id="helper" class="mt-2 px-2 text-sm [overflow-wrap:anywhere] text-muted-foreground">{{ t('live.example') }}</p>

      <p v-if="error" class="text-danger mt-3 flex items-center gap-2 text-sm text-destructive" role="alert">
        <CircleAlert class="size-4 shrink-0" aria-hidden="true" />{{ error }}
      </p>
    </section>

    <!-- Queried event -->
    <EventSection
      v-if="searchHasHappened && roundId"
      id="queried-results"
      :title="queriedEventTitle || t('live.yourQuery')"
      :pgn-list="pgnListAsked"
      :loading="loadingQueried"
      :empty-text="loadedQueried ? t('live.noGames') : ''"
      initially-open
      @refresh="refreshQueriedEvent"
    />

    <!-- Featured event -->
    <template v-if="featuredEvent">
      <h3 class="fs-3 mt-2 text-xl font-semibold text-foreground">{{ t('live.featured') }}</h3>
      <EventSection
        :title="featuredEventTitle || t('live.featured')"
        :pgn-list="pgnListFeatured"
        :loading="loadingFeatured"
        :empty-text="loadedFeatured ? t('live.noGames') : ''"
        initially-open
        @refresh="refreshFeaturedEvent"
      />
    </template>
  </main>
</template>
