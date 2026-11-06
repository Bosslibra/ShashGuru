<script setup lang="ts">
import { ref, watch } from 'vue'
import { isValidFen } from '@/lib/fen'
import { useGameStore } from '@/stores/game'

const game = useGameStore()

// The FEN box follows the board; typing a valid FEN starts a new analysis from that position.
const fenInput = ref(game.currentFen)
watch(
  () => game.currentFen,
  (fen) => (fenInput.value = fen),
)
watch(fenInput, (value) => {
  const fen = value.trim()
  if (fen && fen !== game.currentFen && isValidFen(fen)) game.loadFen(fen)
})

const pgnInput = ref(game.pgnText)
watch(
  () => game.pgnText,
  (text) => (pgnInput.value = text),
)

function loadPgn() {
  try {
    game.loadPgn(pgnInput.value)
  } catch (error) {
    alert(error instanceof Error ? error.message : 'PGN is invalid or empty.')
  }
}
</script>

<template>
  <div>
    <div class="fen-input-container w-100">
      <div class="input-group flex-nowrap mt-2">
        <span class="input-group-text text-white bg-light bg-opacity-25 border border-0 font-monospace">FEN</span>
        <input v-model="fenInput" id="fenInput"
          class="  form-control border px-3 py-2 text-white bg-dark border-0"
          placeholder="Enter FEN (updates automatically)" autocomplete="off" aria-label="FEN Input" />
      </div>
    </div>
    <div class="pgn-input-container">
      <div class="input-group flex-nowrap mt-2">
        <span class="input-group-text text-white bg-light bg-opacity-25 border border-0 font-monospace">PGN</span>
        <input v-model="pgnInput" @keyup.enter="loadPgn" id="pgnInput"
          class="form-control border  px-3 py-2   text-white bg-dark border-0" placeholder="Enter PGN and press Enter"
          autocomplete="off" aria-label="PGN Input" />
      </div>
    </div>
  </div>
</template>

<style scoped>
input::placeholder {
  color: gray;
}

.fen-input-container {
  margin-top: 0.5rem;
}

.pgn-input-container {
  margin-top: 0.5rem;
}

input {
  box-shadow: none !important;
}
</style>
