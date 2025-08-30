<template>
  <div class="evaluation-container">
    <div class="evaluation-bar-wrapper" :class="{ 'disabled': !enabled, 'loading': loading && enabled }">
      <div class="evaluation-bar" :class="{ 'flipped': boardOrientation === 'black' }">
        
        <!-- WIN (white or black depending on orientation) -->
        <div 
          class="eval-section win-section" 
          :style="{ height: winPercent + '%' }"
        >
          <div v-if="winPercent > 15" class="eval-text white-text">
            {{ Math.round(winPercent) }}%
          </div>
        </div>

        <!-- DRAW -->
        <div 
          class="eval-section draw-section" 
          :style="{ height: drawPercent + '%' }"
        >
          <div v-if="drawPercent > 15" class="eval-text">
            {{ Math.round(drawPercent) }}%
          </div>
        </div>

        <!-- LOSS -->
        <div 
          class="eval-section loss-section" 
          :style="{ height: lossPercent + '%' }"
        >
          <div v-if="lossPercent > 15" class="eval-text black-text">
            {{ Math.round(lossPercent) }}%
          </div>
        </div>
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
  </div>
</template>

<script setup>
import { computed, defineProps } from 'vue'

const props = defineProps({
  wdl: {
    type: Object,
    required: true, // { win: number, draw: number, loss: number }
  },
  enabled: {
    type: Boolean,
    default: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  boardOrientation: {
    type: String,
    default: 'white' // 'white' or 'black'
  }
})

const total = computed(() => props.wdl.win + props.wdl.draw + props.wdl.loss || 1)
const winPercent = computed(() => (props.wdl.win / total.value) * 100)
const drawPercent = computed(() => (props.wdl.draw / total.value) * 100)
const lossPercent = computed(() => (props.wdl.loss / total.value) * 100)
</script>

<style scoped>
.evaluation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
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

.win-section {
  background: linear-gradient(to top, #f0f0f0, #d0d0d0);
}
.draw-section {
  background: linear-gradient(to top, #9e9e9e, #bdbdbd);
}
.loss-section {
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

.loading-overlay,
.disabled-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.loading-overlay {
  background-color: rgba(0, 0, 0, 0.2);
}

.disabled-overlay {
  background-color: rgba(0, 0, 0, 0.3);
}

.disabled-text {
  color: #666;
  font-size: 10px;
  font-weight: bold;
  writing-mode: vertical-lr;
  text-orientation: mixed;
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
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
