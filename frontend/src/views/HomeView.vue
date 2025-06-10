<script setup>
import { ref,  watch, nextTick } from 'vue';
import ChessBoard from '@/components/ChessBoard.vue';
import AIChat from '@/components/AIChat.vue';
import { Chess } from 'chess.js';

const fen = ref('');
const moves = ref([]);
const isLoading = ref(false);
const hasPlayerInfo = ref(false);
const hasMoves = ref(false)
const selectedMoveIndex = ref(0);
const moveRefs = ref([]);

// Metadata from PGN
const whitePlayer = ref('');
const blackPlayer = ref('');
const gameResult = ref('');

// Called when ChessBoard emits PGN (full)
function setMovesFromPGN(payload) {

  moveRefs.value = [];
  // Set moves
  moves.value = payload.moves;
  hasMoves.value = true;

  // Set player names and result
  if (payload.headers.White && payload.headers.Black) {
    whitePlayer.value = payload.headers.White;
    blackPlayer.value = payload.headers.Black;
    gameResult.value = payload.headers.Result || '-';
    hasPlayerInfo.value = true;
  } else {
    whitePlayer.value = '';
    blackPlayer.value = '';
    gameResult.value = payload.headers.Result || '-';
  }

  // Use chess.js to set fen from moves
  const chess = new Chess();
  for (const move of payload.moves) {
    chess.move(move);
  }
  selectedMoveIndex.value = payload.moves.length - 1;
  updateFen(chess.fen());
}



function onMoveClicked(index) {
  selectedMoveIndex.value = index;
  const chess = new Chess();
  for (let i = 0; i <= index; i++) {
    chess.move(moves.value[i]);
  }
  updateFen(chess.fen());
}
function backStart() {
  onMoveClicked(0)
}
function backOneMove() {
  if (selectedMoveIndex.value > 0) {
    onMoveClicked(selectedMoveIndex.value - 1)
  }
}
function forwardOneMove() {
  if (selectedMoveIndex.value < moves.value.length) {
    onMoveClicked(selectedMoveIndex.value + 1)
  }
}
function forwardEnd() {
  onMoveClicked(moves.value.length - 1)
}

function updateFen(newFen) {
  fen.value = newFen;
}

function handleLoadingChat(val) {
  isLoading.value = val;
}
watch(selectedMoveIndex, async () => {
  await nextTick()
  const el = moveRefs.value[selectedMoveIndex.value]
  if (el) {
    el.scrollIntoView({ behaviour: 'smooth', block: "nearest", inline: "nearest" })
  }
})
</script>

<template>
  <div id="chessboard" class="d-flex justify-content-evenly mx-5">
    <div class="flex-item m-5 mt-2 p-3" :class="{ 'loading': isLoading }">
      <ChessBoard :fenProp="fen" @updateFen="updateFen" @setMovesFromPGN="setMovesFromPGN" />
    </div>

    <div id="chat-view" class="flex-item flex-fill m-5 rounded-4 rounded-top d-flex flex-column">

      <!-- PLAYER INFO -->
      <div v-if="hasPlayerInfo" id="playerInfo"
        class="container-fill m-0 p-3 justify-content-between  text-light rounded-top " style="max-height: 100px;">
        <div class="row mx-1">
          <div class="col-5  fs-4 text-center ">
            <div class="fw-bold fs-5">White:</div> {{ whitePlayer }}
          </div>
          <div class="col-2 px-5 align-item-center text-center">
            <div class="fs-1 fw-bold">{{ gameResult }}</div>
          </div>
          <div class="col-5 fs-4 text-center">
            <div class="fw-bold fs-5">Black:</div> {{ blackPlayer }}
          </div>
        </div>
      </div>


      <!-- MOVES -->
      <div v-if="hasMoves" class=" fs-5 ">
        <div id="moveHeader" class="d-flex justify-content-center align-items-center  py-3">
          <div>
            <button class="btn btn-sm text-white material-icons" :disabled="selectedMoveIndex === 0"
              @click="backStart">first_page</button>
          </div>
          <div>
            <button class="btn btn-sm text-white material-icons" :disabled="selectedMoveIndex === 0"
              @click="backOneMove">arrow_back</button>
          </div>
          <span class=" fs-5 fw-bold text-center mx-5">Moves</span>
          <div>
            <button class="btn btn-sm text-white material-icons" :disabled="selectedMoveIndex === moves.length -1"
              @click="forwardOneMove">arrow_forward</button>
          </div>
          <div>
            <button class="btn btn-sm text-white material-icons" :disabled="selectedMoveIndex === moves.length -1"
              @click="forwardEnd">last_page</button>
          </div>
        </div>
        <div id="moves" class="p-4 pt-1 pb-2">
          <span :class="{ selected: index === selectedMoveIndex }" @click="onMoveClicked(index)"
            style="cursor:pointer; " v-for="(move, index) in moves" :key="index" :ref="el => moveRefs[index] = el">
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

#chessboard {
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
  max-height: 170px;
  overflow: auto;
  scroll-behavior: smooth;
  border-bottom: 1px solid #ffffff1e;
}

#moveHeader {
  background-color: #2f2d2a;
  border-bottom: 1px solid #ffffff1e;
}
#moveHeader button {
  border: none;
}
#playerInfo {
  background-color: #33312e;
  border-bottom: 1px solid #ffffff1e;
}

/* width */
::-webkit-scrollbar {
  width: 10px;
}

/* Track */
::-webkit-scrollbar-track {}

/* Handle */
::-webkit-scrollbar-thumb {
  background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>