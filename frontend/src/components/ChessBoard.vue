<script setup>
import { ref, reactive } from 'vue';
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';

const emit = defineEmits(['updateFen']);

const boardAPI = ref(null);

const boardConfig = reactive({
  fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", // Starting FEN
  coordinates: false,
  autoCastle: true,
  highlight: {
    lastMove: true, 
    check: true,
  }
});


const fen = ref(boardConfig.fen);

// --- Event Handlers ---

function handleCheckmate(isMated) {
  if (isMated === 'w') {
    alert('Black wins by checkmate!');
  } else if (isMated === 'b') {
    alert('White wins by checkmate!');
  }
}

function handleMove(move) {
  const newFen = move.after;
  fen.value = newFen;
  emit("updateFen", newFen);
}

// --- Board Control ---

function toggleOrientation() {
  boardAPI.value?.board.toggleOrientation();
}

function resetBoard() {
  boardAPI.value?.resetBoard();
  fen.value = boardConfig.fen;
  emit("updateFen", boardConfig.fen);
}

function setPositionFromInput() {
  const trimmedFen = fen.value.trim();
  if (trimmedFen) {
    boardAPI.value?.setPosition(trimmedFen);
    emit("updateFen", trimmedFen);
  }
}
</script>

<template>
  <section role="region" aria-label="Board Controls" class="board-controls">
    <button type="button" @click="toggleOrientation" class="btn btn-sm m-1">
      Flip Board
    </button>
    <button type="button" @click="resetBoard" class="btn btn-sm m-1">
      Starting Position
    </button>
  </section>

  <TheChessboard
    :board-config="boardConfig"
    @board-created="(api) => (boardAPI = api)"
    @checkmate="handleCheckmate"
    @move="handleMove"
  />

  <div class="fen-input-container">
    <input
      v-model="fen"
      @keyup.enter="setPositionFromInput"
      id="fenInput"
      class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white bg-dark border-0"
      placeholder="Enter FEN and press Enter"
      autocomplete="off"
      aria-label="FEN Input"
    />
    </div>
</template>

<style scoped>

.board-controls {
  margin-bottom: 1rem; 
}

.fen-input-container {
  margin-top: 0.5rem;
}

button.btn {
  border-color: #f2f2f2;
  color: #f2f2f2;
  background-color: transparent; 
  transition: color 0.15s ease-in-out, border-color 0.15s ease-in-out; 
}

button.btn:hover {
  border-color: #cdd26a;
  color: #cdd26a;
}

</style>