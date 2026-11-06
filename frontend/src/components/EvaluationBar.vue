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
      <!-- <div class="best-move">
        <span class="label">Best:</span> 
        <span class="move">{{ evaluation.move }}</span>
      </div> -->
      <!-- <div v-if="evaluation.winprob !== null" class="win-probability">
        Win: {{ Math.round(evaluation.winprob * 10) }}%
      </div> -->
    </div>

    <!-- Error display -->
    <div v-if="error && enabled" class="error-container">
      <i class="material-icons" style="color: #ff6b6b;">error</i>
      <div class="error-tooltip bg-danger">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { formatScore, scoreToPercent } from '@/lib/evalFormat'
import { useEvaluationStore } from '@/stores/evaluation'
import { useSettingsStore } from '@/stores/settings'

withDefaults(
  defineProps<{
    /** Which side is at the bottom of the board. */
    boardOrientation?: 'white' | 'black'
  }>(),
  { boardOrientation: 'white' },
)

const { enabled } = storeToRefs(useSettingsStore())
const { current: evaluation, loading, error } = storeToRefs(useEvaluationStore())

// Scores are relative to the side to move *of the evaluated position*, which may differ from the
// position now on the board while a new evaluation is loading.
const whiteToMove = computed(() => evaluation.value?.sideToMove !== 'black')
const bestLine = computed(() => evaluation.value?.lines[0] ?? null)

// Always show the evaluation from White's point of view, regardless of board orientation.
const whitePercentage = computed(() => {
  const ev = evaluation.value
  if (!ev) return 50
  if (ev.status === 'checkmate') return whiteToMove.value ? 0 : 100
  if (!bestLine.value) return 50
  return scoreToPercent(bestLine.value.score, whiteToMove.value, bestLine.value.winprob)
})

const blackPercentage = computed(() => 100 - whitePercentage.value)

const formatEvaluation = () =>
  bestLine.value ? formatScore(bestLine.value.score, whiteToMove.value) : ''
</script>

<style scoped>
/* styles */
.error-container {
  position: relative;      /* important */
  display: inline-block;   /* so hover works neatly around the icon */
}

.error-tooltip {
  visibility: hidden;
  opacity: 0;
  transition: opacity 0.2s ease;
  position: absolute;
  z-index: 9999;           /* sit above surrounding UI */
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  background-color: #ff4444; /* avoid mixing with .bg-danger while testing */
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

.best-move {
  margin-bottom: 5px;
}

.label {
  color: #aaa;
}

.move {
  font-weight: bold;
  color: #cdd26a;
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
