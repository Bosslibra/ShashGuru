<script setup>
import { ref } from 'vue';
import ChessBoard from '@/components/ChessBoard.vue';
import AIChat from '@/components/AIChat.vue';
import { Chess } from 'chess.js';

const fen = ref('');
const moves = ref([]);
const isLoading = ref(false);

// Metadata from PGN
const whitePlayer = ref('');
const blackPlayer = ref('');
const gameResult = ref('');

// Called when ChessBoard emits PGN (full)
function setMovesFromPGN(payload) {
  // payload is the object emitted:
  // { fullPGN: string, moves: array, headers: object }

  console.log(payload.fullPGN);  // full PGN string
  console.log(payload.moves);    // array of moves
  console.log(payload.headers);  // headers object

  // Set moves
  moves.value = payload.moves;

  // Set player names and result
  whitePlayer.value = payload.headers.White || '';
  blackPlayer.value = payload.headers.Black || '';
  gameResult.value = payload.headers.Result || '';

  // Use chess.js to set fen from moves
  const chess = new Chess();
  for (const move of payload.moves) {
    chess.move(move);
  }

  updateFen(chess.fen());
}

const selectedMoveIndex = ref(-1);

function onMoveClicked(index) {
  selectedMoveIndex.value = index;
  const chess = new Chess();
  for (let i = 0; i <= index; i++) {
    chess.move(moves.value[i]);
  }
  updateFen(chess.fen());
}

function updateFen(newFen) {
  fen.value = newFen;
}

function handleLoadingChat(val) {
  isLoading.value = val;
}
</script>

<template>
  <div class="d-flex justify-content-evenly mx-5">
    <div class="flex-item m-5 mt-2 p-3" :class="{ 'loading': isLoading }">
      <ChessBoard :fenProp="fen" @updateFen="updateFen" @setMovesFromPGN="setMovesFromPGN" />
    </div>

    <div id="chat-view" class="flex-item flex-fill m-5 rounded-4 rounded-top d-flex flex-column">

      <!-- PLAYER INFO -->
      <div class="d-flex p-3 justify-content-between border-bottom text-light rounded-top " style="max-height: 100px;">

        <div class="flex-item px-5 text-center">
          <div class="fw-bold fs-5">White:</div> {{ whitePlayer }}
        </div>
        <div class="flex-item px-5 text-center">
          <div class="fs-1 fw-bold">{{ gameResult }}</div>
        </div>
        <div class="flex-item px-5 text-center">
          <div class="fw-bold fs-5">Black:</div> {{ blackPlayer }}
        </div>


      </div>

      <!-- MOVES -->
      <div class="p-4 fs-5 border-bottom">
        <h5 class="text-center">Moves</h5>
        <div id="moves">
          <span :class="{ selected: index === selectedMoveIndex }" @click="onMoveClicked(index)"
            style="cursor:pointer; " v-for="(move, index) in moves" :key="index">
            <span class="text-muted" v-if="index % 2 === 0">
              {{ Math.floor(index / 2 + 1) }}.
            </span>
            <span class="colorize px-2 p-1" v-if="index % 2 === 0">{{ move }}</span>
            <span class="colorize px-1 p-1 me-1" v-else>{{ move }}</span>
          </span>
        </div>
      </div>

      <!-- CHAT -->
      <AIChat :fen="fen" @loadingChat="handleLoadingChat" />
    </div>
  </div>
</template>



<style scoped>
#chat-view {
  background-color: #262421;
  height: 80vh;
}

.d-flex {
  color: aliceblue;
  height: 50%;
}

.selected>.colorize {
  background-color: #cdd26a;
  color: black;
  border-radius: 4px;
  user-select: none;
}

.loading {
  pointer-events: none;
  /* Prevent all interaction */
}

#moves {
  max-height: 130px;
  overflow: auto;
  scroll-behavior: smooth;
}
/* width */
::-webkit-scrollbar {
  width: 10px;
}

/* Track */
::-webkit-scrollbar-track {
  
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>