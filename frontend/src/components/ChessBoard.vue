<script setup>
import { ref, reactive } from 'vue';
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';
import { Chess } from 'chess.js'

const emit = defineEmits(['updateFen', 'setMovesFromPGN']);

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


// --- ROBA NUOVA ---
import { watch } from 'vue';

const props = defineProps({
  fenProp: {
    type: String,
    required: false
  }
});

// Watch for fen changes from parent and update board
watch(() => props.fenProp, (newFen) => {
  if (newFen && boardAPI.value) {
    fen.value = newFen;
    boardAPI.value.setPosition(newFen);

  }
});



//--- FINE


const fen = ref(boardConfig.fen);
const pgn = ref('');
const side = ref('')

watch(fen, () => {
  side.value = fen.value.split(" ")[1]
  console.log(side.value)
})

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

function handlePGN() {
  const chess = new Chess();
  const rawPGN = pgn.value.trim();

  const headerRegex = /\[(\w+)\s+"([^"]+)"\]/g;
  const headers = {};
  let match;

  while ((match = headerRegex.exec(rawPGN)) !== null) {
    headers[match[1]] = match[2];
  }

  const movesOnly = rawPGN.replace(headerRegex, '').replace(/\s+/g, ' ').trim();

  chess.loadPgn(movesOnly);

  if (chess.history().length === 0) {
    alert("PGN is invalid or empty.");
    return;
  }

  const finalFEN = chess.fen();
  fen.value = finalFEN;
  emit("updateFen", finalFEN);
  emit("setMovesFromPGN", {
    fullPGN: rawPGN,
    moves: chess.history(),
    headers,
  });

  boardAPI.value?.setPosition(finalFEN);
}




</script>

<template>
  <div class="d-flex">
    <section role="region" aria-label="Board Controls" class="board-controls">
      <button type="button" @click="toggleOrientation" class="btn btn-sm m-1">
        Flip Board
      </button>
      <button type="button" @click="resetBoard" class="btn btn-sm m-1">
        Starting Position
      </button>

    </section>
    <div v-if="side === 'w'" class="text-white p-2">White to play</div>
    <div v-else-if="side === 'b'" class="text-white p-2">Black to play</div>
  </div>
  <TheChessboard :board-config="boardConfig" @board-created="(api) => (boardAPI = api)" @checkmate="handleCheckmate"
    @move="handleMove" />

  <div class="fen-input-container">
    <input v-model="fen" @keyup.enter="setPositionFromInput" id="fenInput"
      class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white bg-dark border-0"
      placeholder="Enter FEN and press Enter" autocomplete="off" aria-label="FEN Input" />
  </div>
  <div class="pgn-input-container">
    <input v-model="pgn" @keyup.enter="handlePGN" id="pgnInput"
      class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white bg-dark border-0"
      placeholder="Enter PGN and press Enter" autocomplete="off" aria-label="PGN Input" />
  </div>
</template>

<style scoped>
.board-controls {
  margin-bottom: 1rem;
}

.fen-input-container {
  margin-top: 0.5rem;
}

.pgn-input-container {
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