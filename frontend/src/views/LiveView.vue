<script setup>
import { onMounted, ref, nextTick, computed } from 'vue'
import EventSection from '@/components/EventSection.vue'

const eventId = ref('sO7W9Jje')      // Example tournament ID
const roundId = ref('')              // Set directly or extract from URL
const pgnListFeatured = ref([])
const pgnListAsked = ref([])
const loading = ref(false)
const error = ref(null)
const featuredEvent = ref(null)
const isFeatureVisibile = ref(true)
const isQueriedVisibile = ref(true)
const searchHasHappened = ref(false)
const searchInput = ref('')

// Add refresh functions for each event section
async function refreshQueriedEvent() {
  if (roundId.value) {
    const pgnAsked = await fetchPgn(roundId.value)
    if (pgnAsked) {
      pgnListAsked.value = splitPGNs(pgnAsked)
    }
  }
}

async function refreshFeaturedEvent() {
  if (featuredEvent.value) {
    await fetchPgnFeatured()
  }
}

// Fetch tournament info and list of rounds
async function fetchEvent() {
  error.value = null
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/${eventId.value}`)
    if (!res.ok) throw new Error('Event not found')
    const data = await res.json()

    // Pick default round if available
    roundId.value = data.defaultRoundId || (data.rounds[0] && data.rounds[0].id) || ''
  } catch (err) {
    error.value = err.message
  }
}

function splitPGNs(pgnText) {
  //Takes the full PGN list from the Lichess API and splits it into individual games
  return pgnText
    .trim()
    .split(/\n\n(?=\[Event )/) // lookahead for new game start
}

async function fetchQueriedPgn() {
  if (searchInput.value.startsWith('http') || searchInput.value.includes('lichess.org')) {
    setFromUrl(searchInput.value) // Extract IDs from URL
  } else {
    roundId.value = searchInput.value.trim()
  }
  if (roundId.value) {
    const pgnAsked = await fetchPgn(roundId.value)
    if (pgnAsked) {
      pgnListAsked.value = splitPGNs(pgnAsked)
      if (!searchHasHappened.value) {
        searchHasHappened.value = true
        await nextTick()

      }
    }
  }
}

async function fetchPgnFeatured() {
  if (!featuredEvent.value) return
  const pgnFeatured = await fetchPgn(featuredEvent.value)
  if (pgnFeatured !== null) {
    pgnListFeatured.value = splitPGNs(pgnFeatured)
  }
}

function cleanPgnFromComments(pgn) {
  // Remove comments and NAGs from PGN for cleaner display
  return pgn.replace(/\{[^}]*\}/g, '') // Remove comments {...}
    .replace(/\$\d+/g, '')  // Remove NAGs like $1, $2, etc.
    .trim()
}

// Fetch PGNs of a specific round
async function fetchPgn(idToFetch) {
  let pgnText = '';
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/round/${idToFetch}.pgn`)
    if (!res.ok) throw new Error('Could not fetch PGN')
    pgnText = await res.text()
    pgnText = cleanPgnFromComments(pgnText)
    loading.value = false
    return pgnText
  } catch (err) {
    error.value = err.message
    loading.value = false
    return null
  }
}

// Helper: If user pastes a broadcast URL, extract IDs
function setFromUrl(url) {
  try {
    // Example URL: https://lichess.org/broadcast/knight-invitational/sO7W9Jje/eJLgkG7n
    const parts = url.split('/')
    eventId.value = parts[5] || ''
    roundId.value = parts[6].split('#')[0] || ''
  } catch (err) {
    error.value = 'Invalid URL format'
  }
}

const featuredEventTitle = computed(() => {
  if (!pgnListFeatured.value.length) return 'Loading Event Title...'
  const match = pgnListFeatured.value[0].match(/\[Event "(.*?)"\]/)
  return match ? match[1] : 'Event Name Unknown'
})

const queriedEventTitle = computed(() => {
  if (!pgnListAsked.value.length) return 'Loading Event Title...'
  const match = pgnListAsked.value[0].match(/\[Event "(.*?)"\]/)
  return match ? match[1] : 'Event Name Unknown'
})

onMounted(() => {
  // Automatically fetch event info on mount
  featuredEvent.value = import.meta.env.FEATURED_EVENT_ID || 'bFcndX91' // Test featured event ID, should be null in production
  fetchPgnFeatured();
  //fetchTopEvents();
})

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

  <EventSection v-if="searchHasHappened && roundId && isQueriedVisibile" :title="queriedEventTitle || 'Your Query'"
    :pgnList="pgnListAsked" :shouldRender="searchHasHappened" :onRefresh="refreshQueriedEvent" initiallyOpen id="queried-results" />


  <div v-if="featuredEvent" class="fs-3 ms-5 m-4">Featured Event</div>
  <!-- Featured Event -->
  <EventSection v-if="featuredEvent" :title="featuredEventTitle || 'Featured Event'" :pgnList="pgnListFeatured"
    :shouldRender="isFeatureVisibile" :onRefresh="refreshFeaturedEvent" initiallyOpen />

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