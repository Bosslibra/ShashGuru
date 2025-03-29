<script setup>
import { ref } from 'vue';
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';

const boardAPI = ref();
const fen = ref('')

const emit = defineEmits(['updateFen']);

function handleCheckmate(isMated) {
  if (isMated === 'w') {
    alert('Black wins!');
  } else {
    alert('White wins!');
  }
}

function toggleOrientation() {
  boardAPI.value?.board.toggleOrientation();
}

function resetBoard() {
  boardAPI.value?.resetBoard();
}

function setPosition() {
  emit("updateFen", fen.value.trim())
  boardAPI.value?.setPosition(fen.value.trim())
}
</script>

<template>
  <section role="region" aria-label="Board Controls">
    <button type="button" @click="toggleOrientation" class="btn btn-sm m-1">
      Flip Board
    </button>
    <button type="button" @click="resetBoard" class="btn btn-sm m-1">Starting Position</button>
  </section>
  <TheChessboard :board-config="boardConfig" @board-created="(api) => (boardAPI = api)" @checkmate="handleCheckmate" />
  <input v-model="fen" @keyup.enter="setPosition" id="input"
    class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white bg-dark border-0" placeholder="fen"
    autocomplete="off" />
</template>

<style></style>

<script>
export default {
  data() {
    return {
      fen: '',
      boardConfig: {
        fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        coordinates: false,
        autoCastle: true,
        highlight: {
          lastmove: true,
          check: true,
        }
      }
    };
  },
}
</script>

<style>
button.btn {
  border-color: #f2f2f2 !important;
  color: #f2f2f2;
}
</style>