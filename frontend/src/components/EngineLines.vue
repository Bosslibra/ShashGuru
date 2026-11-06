<template>
  <div v-if="lines.length > 0 || loading" class="engine-lines shadow mb-0 pb-0">
    <div class="lines-header rounded-top">
      <span class="header-text fs-6">Engine Analysis</span>
      <span class="depth-badge">Depth {{ depth }}</span>
    </div>
    
    <div class="lines-container rounded-bottom px-0 mb-0">
      <!-- Loading overlay on top of content -->
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <span class="loading-text">Analyzing...</span>
      </div>
      
      <div 
        v-for="(line, index) in displayLines" 
        :key="index"
        class="engine-line"
        :class="{ 'best-line': index === 0 }"
      >
        <div class="line-evaluation">
          <span class="line-rank">{{ index + 1 }}.</span>
          <span class="eval-score" :class="evaluationClass(line)">
            {{ formatEvaluation(line) }}
          </span>
        </div>
        <div class="line-moves">
          <span 
            v-for="(move, moveIndex) in parseMoves(line)" 
            :key="moveIndex"
            class="line-move"
            :class="{ 'white-move': move.isWhite, 'black-move': !move.isWhite }"
            @click="onMoveClicked(move.san)"
          >
            <span v-if="move.moveNumber" class="move-number">{{ move.moveNumber }}.</span>
            {{ move.san }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Chess } from 'chess.js'
import { evalClass as getEvaluationClass, formatScore, isWhiteToMove } from '@/lib/evalFormat'
import { useEvaluationStore } from '@/stores/evaluation'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import type { EngineLine } from '@/types/api'

interface DisplayMove {
  san: string
  uci: string
  isWhite: boolean
  moveNumber: number | null
}

const MAX_DISPLAYED_MOVES = 6

const game = useGameStore()
const { lines, current, loading } = storeToRefs(useEvaluationStore())
const settings = useSettingsStore()

const currentFen = computed(() => game.currentNode.fen)
// Lines belong to the evaluated position; scores are relative to *its* side to move.
const evaluatedFen = computed(() => current.value?.fen ?? currentFen.value)
const whiteToMove = computed(() => isWhiteToMove(evaluatedFen.value))
const depth = computed(() => current.value?.depth || settings.depth)

// Display only the requested number of lines
const displayLines = computed(() => lines.value.slice(0, settings.lines))

function onMoveClicked(move: string) {
  // Only the first line's moves apply to the position on the board.
  game.play(move)
}

// Convert the engine line (UCI) to SAN, starting from the evaluated position
function parseMoves(line: EngineLine): DisplayMove[] {
  const fen = evaluatedFen.value
  if (!line.pv.length || !fen) return []

  const chess = new Chess(fen)
  const fenParts = fen.split(' ')
  let isWhite = fenParts[1] !== 'b'
  let moveNumber = parseInt(fenParts[5]) || 1

  const parsed: DisplayMove[] = []
  for (const uci of line.pv.slice(0, MAX_DISPLAYED_MOVES)) {
    let san = uci
    try {
      san = chess.move({
        from: uci.slice(0, 2),
        to: uci.slice(2, 4),
        promotion: uci.length > 4 ? uci[4] : undefined,
      }).san
    } catch (error) {
      console.warn(`Failed to parse UCI move: ${uci}`, error)
    }
    parsed.push({ san, uci, isWhite, moveNumber: isWhite ? moveNumber : null })
    if (!isWhite) moveNumber++
    isWhite = !isWhite
  }
  return parsed
}

const formatEvaluation = (line: EngineLine) => formatScore(line.score, whiteToMove.value)
const evaluationClass = (line: EngineLine) => getEvaluationClass(line.score, whiteToMove.value)
</script>

<style scoped>
.engine-lines {
  /*background: rgba(42, 42, 42, 0.95);*/
  
  overflow: hidden;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.lines-header {
  background-color: #444;

  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-text {
  color: #e8e8e8;
  font-weight: 600;
  font-size: 0.9rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.depth-badge {
  background: #cdd26a;
  color: black;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.lines-container {
  position: relative; /* Allow absolute positioning of overlay */
  padding: 8px 0;
  min-height: 120px; /* Ensure consistent height */
  border: 1px solid #444;
  border-top: 0px solid transparent;
  border-radius: 0, 0, 8px, 8px;
  margin-bottom: 12px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(42, 42, 42, 0.9); /* Semi-transparent background */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 10; /* Ensure it's on top */
  border-radius: 0 0 8px 8px; /* Match container border radius */
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(205, 210, 106, 0.3);
  border-top: 2px solid #cdd26a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  color: #e8e8e8;
  font-size: 0.85rem;
  font-weight: 500;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.engine-line {
  display: flex;
  padding: 6px 12px;
  transition: background-color 0.2s ease;
  cursor: pointer;
  border-left: 3px solid transparent; /* Keeps consistent spacing with best line */
}

.engine-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.engine-line.best-line {
  background: rgba(205, 210, 106, 0.1);
  border-left: 3px solid #cdd26a;
}

.line-evaluation {
  flex-shrink: 0;
  width: 70px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.line-rank {
  color: #adb5bd;
  font-size: 0.8rem;
  font-weight: 500;
  width: 20px;
}

.eval-score {
  font-weight: 600;
  font-size: 0.85rem;
  min-width: 45px;
  text-align: center;
}

.eval-score.white-winning {
  color: #4fc3f7;
}

.eval-score.white-better {
  color: #81c784;
}

.eval-score.white-slightly-better {
  color: #aed581;
}

.eval-score.neutral {
  color: #bdbdbd;
}

.eval-score.black-slightly-better {
  color: #ffab91;
}

.eval-score.black-better {
  color: #ff8a65;
}

.eval-score.black-winning {
  color: #f48fb1;
}

.line-moves {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  padding-left: 8px;
}

.line-move {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  cursor: pointer;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
}

.line-move:hover {
  background: rgba(205, 210, 106, 0.2);
  transform: translateY(-1px);
}

.line-move.white-move {
  background: rgba(255, 255, 255, 0.1);
  color: #f0f0f0;
}

.line-move.black-move {
  background: rgba(0, 0, 0, 0.3);
  color: #d0d0d0;
}

.move-number {
  font-weight: 600;
  color: #adb5bd;
  font-size: 0.8rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .line-evaluation {
    width: 60px;
  }
  
  .line-moves {
    padding-left: 4px;
  }
  
  .line-move {
    font-size: 0.8rem;
    padding: 1px 4px;
  }
}
</style>
