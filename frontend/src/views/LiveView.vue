<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EventSection from '@/components/EventSection.vue'
import { fetchRoundPgn } from '@/api/lichess'
import { parseBroadcastInput, parseHeaders, splitPgns } from '@/lib/pgn'

// Lichess broadcast round shown as "Featured Event" (a test round; empty it in production)
const featuredEvent = ref(import.meta.env.VITE_FEATURED_EVENT_ID || 'bFcndX91')

const roundId = ref('')
const pgnListFeatured = ref<string[]>([])
const pgnListAsked = ref<string[]>([])
const loadingFeatured = ref(false)
const loadingQueried = ref(false)
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
    error.value = err instanceof Error ? err.message : 'Could not fetch PGN'
    return null
  }
}

async function refreshQueriedEvent() {
  if (!roundId.value) return
  loadingQueried.value = true
  const games = await loadRound(roundId.value)
  if (games) pgnListAsked.value = games
  loadingQueried.value = false
}

async function fetchQueriedPgn() {
  const parsed = parseBroadcastInput(searchInput.value)
  if (!parsed) {
    error.value = 'Invalid Lichess broadcast URL or round ID'
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
}

function eventTitle(games: string[]): string {
  if (!games.length) return 'Loading Event Title...'
  return parseHeaders(games[0]).Event || 'Event Name Unknown'
}

const featuredEventTitle = computed(() => eventTitle(pgnListFeatured.value))
const queriedEventTitle = computed(() => eventTitle(pgnListAsked.value))

onMounted(refreshFeaturedEvent)
</script>

<template>

  <div class="p-4 mx-5">
    <div class="container py-4 w-100">
      <h2 class="text-center text-light mb-4 mx">Events and Broadcasts</h2>

      <!-- Search Bar -->
      <div id="search-group" class="input-group rounded-pill  p-1">
        <input id="input-event" type="text" class="form-control outline-none rounded-pill me-1" v-model="searchInput"
          @keyup.enter="fetchQueriedPgn" placeholder="Paste Lichess Broadcast URL or Event ID..." />

        <!-- Search Button -->
        <button id="search-button" class="btn rounded-circle" type="button" @click="fetchQueriedPgn"
          :disabled="loading">
          <span class="material-icons mt-1" v-if="!loading">search</span>
          <span v-else class="spinner-border spinner-border-sm"></span>
        </button>
      </div>

      <!-- Helper text -->
      <small id="helper" class="form-text  mt-2 ms-1">
        Example: https://lichess.org/broadcast/.../sO7W9Jje/eJLgkG7n or eJLgkG7n
      </small>

      <!-- Error Message -->
      <div v-if="error" class="text-danger mt-3">
        ⚠️ {{ error }}
      </div>
    </div>
  </div>

  <!-- Queried Event -->

  <EventSection v-if="searchHasHappened && roundId" :title="queriedEventTitle || 'Your Query'"
    :pgnList="pgnListAsked" :loading="loadingQueried" @refresh="refreshQueriedEvent" initiallyOpen id="queried-results" />


  <div v-if="featuredEvent" class="fs-3 ms-5 m-4">Featured Event</div>
  <!-- Featured Event -->
  <EventSection v-if="featuredEvent" :title="featuredEventTitle || 'Featured Event'" :pgnList="pgnListFeatured"
    :loading="loadingFeatured" @refresh="refreshFeaturedEvent" initiallyOpen />

  <footer class="mb-5"></footer>
</template>


<style scoped>
#search-group,
#input-event {
  background-color: #232323 !important;
  border: none !important;
  color: white;
  outline: none;
  box-shadow: none;
}

#search-group {
  border: 1px solid #aaa23a !important;
}

#helper,
#input-event::placeholder {
  color: #ebebeba3;
}

#search-button {
  background-color: #aaa23a !important;
  border: 1px solid #aaa23a !important;
  color: white;
}
</style>