<template>
  <div class="evaluation-container">
    <div class="evaluation-bar-wrapper" :class="{ 'disabled': !enabled, 'loading': loading && enabled }">
      <div class="evaluation-bar" :class="{ 'flipped': boardOrientation === 'black' }">
        <template v-if="enabled">
          <!-- Top section (black when white orientation, white when black orientation) -->
          <div class="eval-section" :class="boardOrientation !== 'white' ? 'black-section' : 'white-section'"
            :style="{ height: (boardOrientation !== 'white' ? blackPercentage : whitePercentage) + '%' }">
            <div v-if="(boardOrientation !== 'white' ? blackPercentage : whitePercentage) > 15" class="eval-text"
              :class="boardOrientation !== 'white' ? 'black-text' : 'white-text'">
              {{ formatEvaluation() }}
            </div>
          </div>

          <!-- Bottom section (white when white orientation, black when black orientation) -->
          <div class="eval-section" :class="boardOrientation !== 'white' ? 'white-section' : 'black-section'"
            :style="{ height: (boardOrientation !== 'white' ? whitePercentage : blackPercentage) + '%' }">
            <div v-if="(boardOrientation !== 'white' ? whitePercentage : blackPercentage) > 15" class="eval-text"
              :class="boardOrientation !== 'white' ? 'white-text' : 'black-text'">
              {{ formatEvaluation() }}
            </div>
          </div>
        </template>

        <template v-else>
          <!-- Disabled state - neutral position -->
          <div class="eval-section black-section" style="height: 50%"></div>
          <div class="eval-section white-section" style="height: 50%"></div>
        </template>
      </div>

      <!-- Center line -->
      <div class="center-line"></div>

      <!-- Loading overlay -->
      <div v-if="loading && enabled" class="loading-overlay">
        <div class="spinner"></div>
      </div>

      <!-- Disabled overlay -->
      <div v-if="!enabled" class="disabled-overlay">
        <span class="disabled-text">OFF</span>
      </div>
    </div>

    <!-- Evaluation details -->
    <div v-if="evaluation && enabled" class="evaluation-details">
      <div v-if="winProbability !== null" class="win-probability">
        Win: {{ winProbability }}%
      </div>
    </div>

    <!-- Error display -->
    <div v-if="error && enabled" class="error-container">
      <i class="material-icons" @mouseover="isErrorTooltipVisible = true" @mouseleave="isErrorTooltipVisible = false"
        style="color: #ff6b6b;">error</i>
      <div class="error-tooltip bg-danger">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { EvaluationService } from '@/services/evaluationService.js'
import { DEFAULT_DEPTH, DEFAULT_EVALUATION_ENABLED, DEFAULT_SHOW_LINES } from '@/constants/evaluation.js'

const emit = defineEmits(['evaluation-update', 'loading-update'])

const props = defineProps({
  fen: {
    type: String,
    required: true
  },
  depth: {
    type: Number,
    default: DEFAULT_DEPTH
  },
  enabled: {
    type: Boolean,
    default: DEFAULT_EVALUATION_ENABLED
  },
  boardOrientation: {
    type: String,
    default: 'white' // 'white' or 'black'
  },
  barHeight: {
    type: Number,
    default: 800
  },
  showLines: {
    type: Number,
    default: DEFAULT_SHOW_LINES
  }
})

const evaluation = ref(null)
const loading = ref(false)
const error = ref(null)
const evaluationSideToMove = ref(true) // Store whose turn it was when evaluation was calculated
const lastValidPercentage = ref(50) // Store the last valid percentage to avoid flipping during loading
const isErrorTooltipVisible = ref(false)
const winProbability = ref(null)

// Helper function to determine whose turn it is from FEN
const isWhiteToMove = computed(() => {
  if (!props.fen) return true
  const fenParts = props.fen.split(' ')
  return fenParts[1] === 'w'
})

// Convert evaluation score to percentage (0-100)
const evaluationPercentage = computed(() => {
  // If we're loading a new evaluation, keep showing the previous evaluation unchanged
  if (loading.value && evaluation.value) {
    return lastValidPercentage.value
  }
  
  if (!evaluation.value) return 50 // Neutral position
  
  let score = 0
  
  if (evaluation.value.mate !== null) {
    // Mate situation - extreme values
    let mateValue = evaluation.value.mate
    if (!evaluationSideToMove.value) {
      mateValue = -mateValue
    }
    
    if (mateValue > 0) {
      return 100 // White mate - white advantage
    } else {
      return 0 // Black mate - black advantage
    }
  } else if (evaluation.value.score !== null) {
    // Use WDL model to compute win probability
    score = evaluation.value.score
    if (!evaluationSideToMove.value) {
      score = -score
    }
    
    // Calculate win probability using WDL model
    try {
      const { win, draw } = calculateWDL(score, evaluation.value.fen || props.fen)
      const win_probability = Math.floor((2 * win + draw) / 20.0 + 0.5)
      winProbability.value = win_probability
      return Math.max(5, Math.min(95, win_probability))
    } catch (err) {
      console.warn('WDL calculation failed, falling back to score display:', err)
      winProbability.value = null
      // Fallback to traditional evaluation
      const normalizedScore = Math.max(-1000, Math.min(1000, score))
      return Math.max(5, Math.min(95, 50 + (normalizedScore / 20)))
    }
  } else if (evaluation.value.winprob !== null) {
    // Use win probability if available
    let winProb = evaluation.value.winprob
    if (!evaluationSideToMove.value) {
      winProb = 1.0 - winProb
    }
    winProbability.value = Math.round(winProb * 100)
    return winProbability.value
  }
  
  return 50
})

// Always show evaluation from White's POV, regardless of board orientation
const whitePercentage = computed(() => {
  return evaluationPercentage.value
})

const blackPercentage = computed(() => 100 - whitePercentage.value)

const lastValidEvaluation = ref('')

// JS implementation of the Python WDLCalculator (uses only FEN and score)
const as_coeff = [-13.50030198, 40.92780883, -36.82753545, 386.83004070]
const bs_coeff = [96.53354896, -165.79058388, 90.89679019, 49.29561889]

function parseMaterialFromFen(fen) {
  // fen piece placement is the first field
  const parts = fen.split(' ')
  if (!parts || parts.length === 0) return 0
  const placement = parts[0]
  // Count pieces (both colors). Uppercase = white, lowercase = black.
  let counts = { p:0, n:0, b:0, r:0, q:0 }
  for (const ch of placement) {
    const lower = ch.toLowerCase()
    if (counts.hasOwnProperty(lower)) counts[lower]++
  }
  // material: pawns*1 + knights*3 + bishops*3 + rooks*5 + queens*9
  return counts['p'] * 1 + counts['n'] * 3 + counts['b'] * 3 + counts['r'] * 5 + counts['q'] * 9
}

function winRateParams(material) {
  const m = Math.max(17, Math.min(78, material)) / 58.0
  const a = ((as_coeff[0] * m + as_coeff[1]) * m + as_coeff[2]) * m + as_coeff[3]
  const b = ((bs_coeff[0] * m + bs_coeff[1]) * m + bs_coeff[2]) * m + bs_coeff[3]
  return {a,b}
}

function calculateWDL(score, fen) {
  // score in centipawns
  const material = parseMaterialFromFen(fen)
  const score_clamped = Math.max(-4000, Math.min(4000, score))
  const {a,b} = winRateParams(material)
  const win = 1000.0 / (1.0 + Math.exp((a - score_clamped) / b))
  const loss = 1000.0 / (1.0 + Math.exp((a - (-score_clamped)) / b))
  const draw = 1000.0 - win - loss
  return { win: Math.round(win), draw: Math.round(draw), loss: Math.round(loss) }
}

const formatEvaluation = () => {
  // If we're loading a new evaluation, keep showing the previous evaluation text unchanged
  if (loading.value && evaluation.value) {
    return lastValidEvaluation.value
  }
  
  if (!evaluation.value) return ''
  
  if (evaluation.value.mate !== null) {
    let mateValue = evaluation.value.mate
    if (!evaluationSideToMove.value) {
      mateValue = -mateValue
    }
    const mateSign = mateValue >= 0 ? '+' : ''
    return `M${mateSign}${mateValue}`
  } else if (evaluation.value.score !== null) {
    let score = evaluation.value.score
    if (!evaluationSideToMove.value) {
      score = -score
    }
    
    // Try to use WDL-based evaluation text
    try {
      const { win, draw } = calculateWDL(score, evaluation.value.fen || props.fen)
      const win_probability = Math.floor((2 * win + draw) / 20.0 + 0.5)
      return `${win_probability}%`
    } catch (err) {
      // Fallback to traditional score display
      const scoreInPawns = score / 100
      const sign = scoreInPawns >= 0 ? '+' : ''
      return `${sign}${scoreInPawns.toFixed(1)}`
    }
  }
  
  return ''
}

const fetchEvaluation = async () => {
  if (!props.fen || !props.enabled) {
    evaluation.value = null
    evaluationSideToMove.value = true
    winProbability.value = null
    // Emit null evaluation and stop loading
    emit('evaluation-update', {
      bestMove: null,
      evaluation: null,
      depth: 0,
      lines: []
    })
    emit('loading-update', false)
    return
  }
  
  try {
    loading.value = true
    error.value = null
    winProbability.value = null
    
    // Emit loading state
    emit('loading-update', true)
    
    // Store whose turn it is BEFORE making the request
    evaluationSideToMove.value = isWhiteToMove.value
    
    const result = await EvaluationService.fetchEvaluation(props.fen, props.depth, props.showLines)

    if (result.fen === props.fen){
      evaluation.value = result
      
      // Emit evaluation data
      emit('evaluation-update', {
        fen: result?.fen,
        bestMove: result?.move || null,
        evaluation: result?.score || result?.mate || null,
        depth: props.depth,
        lines: result?.lines || []
      })
    }
  } catch (err) {
    console.error('Error fetching evaluation:', err)
    error.value = 'Failed to get evaluation'
    evaluation.value = null
    evaluationSideToMove.value = true
    winProbability.value = null
    // Emit null evaluation on error
    emit('evaluation-update', {
      bestMove: null,
      evaluation: null,
      depth: 0,
      lines: []
    })
  } finally {
    if (evaluation.value?.fen === props.fen) {
      loading.value = false
      // Emit loading state
      emit('loading-update', false)
    }
  }
}

// Watch for FEN changes and fetch new evaluation
watch(() => props.fen, fetchEvaluation, { immediate: true })
watch(() => props.depth, fetchEvaluation)
watch(() => props.enabled, fetchEvaluation)
watch(() => props.showLines, fetchEvaluation)
watch(() => props.boardOrientation, () => {
  // No need to refetch, just update the display
})

// Watch for evaluation changes to update the last valid percentage
watch([evaluation, loading], ([newEval, isLoading]) => {
  if (newEval && !isLoading) {
    let score = 0

    if (newEval.mate !== null) {
      let mateValue = newEval.mate
      if (!evaluationSideToMove.value) {
        mateValue = -mateValue
      }
      lastValidPercentage.value = mateValue > 0 ? 100 : 0
      const mateSign = mateValue >= 0 ? '+' : ''
      lastValidEvaluation.value = `M${mateSign}${mateValue}`
      winProbability.value = mateValue > 0 ? 100 : 0
    } else if (newEval.score !== null) {
      score = newEval.score
      if (!evaluationSideToMove.value) {
        score = -score
      }
      
      const fenToUse = newEval.fen || props.fen || ''
      try {
        const { win, draw } = calculateWDL(score, fenToUse)
        let win_probability = Math.floor((2 * win + draw) / 20.0 + 0.5)
        lastValidPercentage.value = Math.max(5, Math.min(95, win_probability))
        lastValidEvaluation.value = `${win_probability}%`
        winProbability.value = win_probability
      } catch (err) {
        const normalizedScore = Math.max(-1000, Math.min(1000, score))
        lastValidPercentage.value = Math.max(5, Math.min(95, 50 + (normalizedScore / 20)))
        const scoreInPawns = score / 100
        const sign = scoreInPawns >= 0 ? '+' : ''
        lastValidEvaluation.value = `${sign}${scoreInPawns.toFixed(1)}`
        winProbability.value = null
        console.warn('WDL calculation failed, falling back to score display:', err)
      }
    } else if (newEval.winprob !== null) {
      let winProb = newEval.winprob
      if (!evaluationSideToMove.value) {
        winProb = 1.0 - winProb
      }
      const winPct = Math.round(winProb * 100)
      lastValidPercentage.value = winPct
      lastValidEvaluation.value = `${winPct}%`
      winProbability.value = winPct
    }
  }
})
</script>

<style scoped>
/* styles */
.error-container {
  position: relative;
  display: inline-block;
}

.error-tooltip {
  visibility: hidden;
  opacity: 0;
  transition: opacity 0.2s ease;
  position: absolute;
  z-index: 9999;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  background-color: #ff4444;
  color: #fff;
  padding: 8px 10px;
  border-radius: 4px;
  white-space: nowrap;
}

.error-tooltip::after {
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: #ff4444 transparent transparent transparent;
}

.error-container:hover .error-tooltip {
  visibility: visible;
  opacity: 1;
}

.evaluation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 5px;
  height: 100%;
}

.evaluation-bar-wrapper {
  position: relative;
  width: 40px;
  border: 2px solid #444;
  border-radius: 4px;
  overflow: hidden;
  background-color: #222;
  flex: 1;
}

.evaluation-bar-wrapper.disabled {
  opacity: 0.5;
}

.evaluation-bar-wrapper.loading {
  opacity: 0.6;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  z-index: 20;
}

.disabled-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.disabled-text {
  color: #666;
  font-size: 10px;
  font-weight: bold;
  writing-mode: vertical-lr;
  text-orientation: mixed;
}

.evaluation-bar {
  display: flex;
  flex-direction: column-reverse;
  width: 100%;
  height: 100%;
  position: relative;
}

.eval-section {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: height 0.3s ease;
  position: relative;
}

.white-section {
  background: linear-gradient(to top, #f0f0f0, #d0d0d0);
}

.black-section {
  background: linear-gradient(to bottom, #1a1a1a, #333);
}

.eval-text {
  font-size: 10px;
  font-weight: bold;
  writing-mode: vertical-lr;
  text-orientation: mixed;
  transform: rotate(180deg);
}

.white-text {
  color: #000;
}

.black-text {
  color: #fff;
}

.center-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #666;
  transform: translateY(-50%);
  z-index: 10;
}

.evaluation-details {
  text-align: center;
  font-size: 12px;
  color: #f2f2f2;
}

.win-probability {
  color: #bbb;
  font-size: 11px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid #cdd26a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.error-message {
  color: #ff6b6b;
  font-size: 11px;
  text-align: center;
}
</style>