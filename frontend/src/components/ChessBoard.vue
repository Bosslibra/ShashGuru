<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';
import { Chess } from 'chess.js'
import EvaluationBar from './EvaluationBar.vue'
import EvaluationSettings from './EvaluationSettings.vue'
import { DEFAULT_DEPTH, DEFAULT_SHOW_LINES, DEFAULT_EVALUATION_ENABLED, DEFAULT_SHOW_BEST_MOVE } from '@/constants/evaluation.js'
import { useChessStore } from '@/stores/useChessStore'; // TODO: Refactor to only use pinia store for PGN management
import { storeToRefs } from 'pinia';

const chessStore = useChessStore();
const currentPGN = storeToRefs(chessStore).currentPGN;
const emit = defineEmits(['updateFen', 'setMovesFromPGN', 'moveAdded', 'engineEvaluationUpdate', 'showLinesUpdate', 'evaluationLoadingUpdate', 'depthUpdate']);

const boardAPI = ref(null);
const chessboardHeight = ref(400); // Default height

// Evaluation settings
const evaluationDepth = ref(DEFAULT_DEPTH);
const evaluationEnabled = ref(DEFAULT_EVALUATION_ENABLED);
const showBestMoveArrow = ref(DEFAULT_SHOW_BEST_MOVE);
const showLines = ref(DEFAULT_SHOW_LINES);

// Watch for showLines changes and emit to parent
watch(showLines, (newValue) => {
  emit('showLinesUpdate', newValue);
});

// Watch for evaluationDepth changes and emit to parent
watch(evaluationDepth, (newValue) => {
  emit('depthUpdate', newValue);
});


// Board orientation tracking
const boardOrientation = ref('white'); // 'white' or 'black'

// Engine evaluation data
const engineEvaluation = ref({
  bestMove: null,
  evaluation: null,
  depth: 0,
  lines: []
});

// Settings modal
const showSettings = ref(false);

const boardConfig = reactive({
  fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", // Starting FEN
  coordinates: true,
  autoCastle: true,
  highlight: {
    lastMove: true,
    check: true,
  },
  events: {
    select: () => {
      drawBestMovesArrows();
    }
  }
});


// --- ROBA NUOVA ---

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
  // Update board position when FEN changes
  if (fen.value.trim() && boardAPI.value) {
    try {
      boardAPI.value.setPosition(fen.value.trim());
      emit("updateFen", fen.value.trim());
    } catch (error) {
      console.error('Invalid FEN position:', error);
    }
  }
})

// --- Event Handlers ---

function handleBoardCreated(api) {
  boardAPI.value = api;
  // Get chessboard height after it's created
  nextTick(() => {
    updateChessboardHeight();
  });
}

function drawBestMovesArrows() {
  if (showBestMoveArrow.value && engineEvaluation.value?.bestMove) {
    boardAPI.value?.drawMove(
      engineEvaluation.value.bestMove.slice(0, 2),
      engineEvaluation.value.bestMove.slice(2, 4),
      'paleBlue',
    );
  }
}

// Method to receive evaluation data from EvaluationBar
function handleEvaluationUpdate(evalData) {
  engineEvaluation.value = evalData;
  drawBestMovesArrows();
  // Emit the evaluation update to parent component
  emit('engineEvaluationUpdate', evalData);
}

// Method to handle loading state from EvaluationBar
function handleEvaluationLoadingUpdate(isLoading) {
  emit('evaluationLoadingUpdate', isLoading);
}

function updateChessboardHeight() {
  if (boardAPI.value) {
    try {
      const boardElement = boardAPI.value.board.el;
      if (boardElement) {
        const rect = boardElement.getBoundingClientRect();
        chessboardHeight.value = rect.height || 400;
      }
    } catch (error) {
      console.error('Could not get board height, using default', error);
      chessboardHeight.value = 400;
    }
  }
}

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

  // Emit the move to be added to the tree structure
  emit("moveAdded", {
    move: move.san || move.notation,
    fen: newFen,
    from: move.from,
    to: move.to
  });
}

// --- Board Control ---

function toggleOrientation() {
  boardAPI.value?.board.toggleOrientation();
  boardOrientation.value = boardOrientation.value === 'white' ? 'black' : 'white';
  // Update height after orientation change
  nextTick(() => {
    updateChessboardHeight();
  });
}

function resetBoard() {
  boardAPI.value?.resetBoard();
  fen.value = boardConfig.fen;
  emit("updateFen", boardConfig.fen);
  
  // Reset engine evaluation data
  engineEvaluation.value = {
    bestMove: null,
    evaluation: null,
    depth: 0,
    lines: []
  };
  
  // Emit reset signals to parent
  emit('engineEvaluationUpdate', engineEvaluation.value);
  emit('setMovesFromPGN', {
    fullPGN: '',
    moves: [],
    headers: {}
  });
  pgn.value = ''; // Reset PGN input
  chessStore.setPGN(''); // Reset store PGN
  // Update height after reset
  nextTick(() => {
    updateChessboardHeight();
  });
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
  chessStore.setPGN(rawPGN);
  emit("setMovesFromPGN", {
    fullPGN: rawPGN,
    moves: chess.history(),
    headers,
  });

  boardAPI.value?.setPosition(finalFEN);
}

// Initialize chessboard height on mount
onMounted(() => {
  console.log("STORE PGN",chessStore.currentPGN);
  pgn.value = chessStore.currentPGN || null;
  if (pgn.value) {
    handlePGN();
  } 
  // Wait a bit for the chessboard to render
  setTimeout(() => {
    updateChessboardHeight();
  }, 500);

  // Add keyboard listener for modal
  document.addEventListener('keydown', handleKeydown);
});

// Handle keyboard events
function handleKeydown(event) {
  if (event.key === 'Escape' && showSettings.value) {
    showSettings.value = false;
  }
}
watch(currentPGN, (newPGN) => {
  if (newPGN) {
    pgn.value = newPGN;
    handlePGN();
  }
});


// Cleanup on unmount
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});


</script>

<template>
  <div class="chessboard-container" >
    <div class="board-section w-100">
      <div class="d-flex">
        <section role="region" aria-label="Board Controls" class="board-controls">
          <button type="button" @click="toggleOrientation" class="btn btn-sm m-1">
            Flip Board
          </button>
          <button type="button" @click="resetBoard" class="btn btn-sm m-1">
            Starting Position
          </button>
          <button type="button" @click="showSettings = !showSettings" class="btn btn-sm m-1">
            Settings
          </button>
        </section>
        <div v-if="side === 'w'" class="text-white p-2">White to play</div>
        <div v-else-if="side === 'b'" class="text-white p-2">Black to play</div>
      </div>

      <div class="board-with-eval">
        <div class="evaluation-panel">
          <EvaluationBar 
            :fen="fen" 
            :depth="evaluationDepth" 
            :enabled="evaluationEnabled"
            :board-orientation="boardOrientation"
            :bar-height="chessboardHeight" 
            :show-lines="showLines"
            @evaluation-update="handleEvaluationUpdate"
            @loading-update="handleEvaluationLoadingUpdate"
          />
        </div>
        <div class="chessboard-container-wrapper">
          <TheChessboard 
            ref="chessboardRef"
            :board-config="boardConfig" 
            @board-created="handleBoardCreated" 
            @checkmate="handleCheckmate"
            @move="handleMove" 
            style="max-height: 70vh; max-width: 70vmin; min-width: 50vmin; "
            class=""
          />
        </div>
      </div>

      <div class="fen-input-container w-100">
        <div class="input-group flex-nowrap mt-2">
          <span class="input-group-text text-white bg-light bg-opacity-25 border border-0 font-monospace">FEN</span>
          <input v-model="fen" id="fenInput"
            class="  form-control border px-3 py-2 text-white bg-dark border-0"
            placeholder="Enter FEN (updates automatically)" autocomplete="off" aria-label="FEN Input" />
        </div>
      </div>
      <div class="pgn-input-container">
        <div class="input-group flex-nowrap mt-2">
          <span class="input-group-text text-white bg-light bg-opacity-25 border border-0 font-monospace">PGN</span>
          <input v-model="pgn" @keyup.enter="handlePGN" id="pgnInput"
            class="form-control border  px-3 py-2   text-white bg-dark border-0" placeholder="Enter PGN and press Enter"
            autocomplete="off" aria-label="PGN Input" />
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="settings-modal-overlay" @click="showSettings = false">
      <div class="settings-modal" @click.stop>
        <div class="settings-modal-header">
          <h5 class="modal-title">Evaluation Settings</h5>
          <button @click="showSettings = false" class="close-btn material-icons">close</button>
        </div>
        <div class="settings-modal-body">
          <EvaluationSettings v-model:depth="evaluationDepth" v-model:enabled="evaluationEnabled"
            v-model:showBestMove="showBestMoveArrow" v-model:showLines="showLines" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
input::placeholder {
  color: gray;
}
.chessboard-container {
  width: 100%;
}

.board-section {
  display: flex;
  flex-direction: column;
}

.board-with-eval {
  display: flex;
  align-items: stretch;
  gap: 15px;
  height: 100%;
}

.evaluation-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.chessboard-container-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
}

.settings-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.settings-modal {
  background-color: #262421;
  border-radius: 12px;
  border: 1px solid #ffffff1e;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  min-width: 300px;
  max-width: 400px;
  animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }

  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.settings-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 20px 10px 20px;
  border-bottom: 1px solid #ffffff1e;
}

.modal-title {
  color: #f2f2f2;
  margin: 0;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: #f2f2f2;
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  transition: all 0.2s ease;
  font-size: 20px;
}

.close-btn:hover {
  color: #cdd26a;
  background-color: rgba(205, 210, 106, 0.1);
}

.settings-modal-body {
  padding: 20px;
}

.board-controls {
  margin-bottom: 1rem;
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

button.btn {
  background: #262421;
  color: #f2f2f2;
  border: none;
  font-weight: 600;
  border-radius: 6px;
  padding: 0.5em 1.2em;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}

button.btn:hover {
  background: #cdd26a;
  color: #232323;
  box-shadow: 0 4px 16px rgba(205, 210, 106, 0.15);
}
</style>