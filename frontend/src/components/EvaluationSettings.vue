<template>
  <div class="evaluation-settings">
    <div class="settings-header">
      <h6 class="settings-title">Engine Analysis</h6>
      <div class="toggle-container">
        <label class="toggle-switch">
          <input 
            type="checkbox" 
            v-model="localEnabled"
            @change="updateEnabled"
          />
          <span class="slider"></span>
        </label>
        <span class="toggle-label">{{ localEnabled ? 'ON' : 'OFF' }}</span>
      </div>
    </div>
    
    <div v-if="localEnabled" class="setting-item">
      <label for="depth-slider" class="setting-label">
        Depth: {{ localDepth }}
      </label>
      <input 
        id="depth-slider"
        type="range" 
        v-model="localDepth" 
        :min="MIN_DEPTH" 
        :max="MAX_DEPTH" 
        step="1"
        class="setting-slider"
        @input="updateDepth"
      />
    </div>
    
    <div v-if="localEnabled" class="setting-item">
      <div class="setting-toggle">
        <label class="setting-label">Show Best Move Arrow</label>
        <div class="toggle-container-small">
          <label class="toggle-switch-small">
            <input 
              type="checkbox" 
              v-model="localShowBestMove"
              @change="updateShowBestMove"
            />
            <span class="slider-small"></span>
          </label>
          <!-- <span class="toggle-label-small">{{ localShowBestMove ? 'ON' : 'OFF' }}</span> -->
        </div>
      </div>
    </div>

    <div v-if="localEnabled" class="setting-item">
      <label for="lines-slider" class="setting-label">
        Show Lines: {{ localShowLines }}
      </label>
      <input 
        id="lines-slider"
        type="range" 
        v-model="localShowLines" 
        :min="MIN_SHOW_LINES" 
        :max="MAX_SHOW_LINES" 
        step="1"
        class="setting-slider"
        @input="updateShowLines"
      />
    </div>
    
    <div v-if="localEnabled" class="setting-item">
      <button 
        @click="resetToDefaults" 
        class="btn btn-sm reset-btn"
      >
        Reset to Default
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { DEFAULT_DEPTH, DEFAULT_EVALUATION_ENABLED, DEFAULT_SHOW_BEST_MOVE, DEFAULT_SHOW_LINES, MIN_DEPTH, MAX_DEPTH, MIN_SHOW_LINES, MAX_SHOW_LINES } from '@/constants/evaluation.js'

const props = defineProps({
  depth: {
    type: Number,
    default: DEFAULT_DEPTH
  },
  enabled: {
    type: Boolean,
    default: DEFAULT_EVALUATION_ENABLED
  },
  showBestMove: {
    type: Boolean,
    default: DEFAULT_SHOW_BEST_MOVE
  },
  showLines: {
    type: Number,
    default: DEFAULT_SHOW_LINES
  }
})

const emit = defineEmits(['update:depth', 'update:enabled', 'update:showBestMove', 'update:showLines'])

const localDepth = ref(props.depth)
const localEnabled = ref(props.enabled)
const localShowBestMove = ref(props.showBestMove)
const localShowLines = ref(props.showLines)

// Track original depth to compare on close
const originalDepth = ref(props.depth)

const updateDepth = () => {
  // Don't emit immediately, just update local value
  // The depth will be emitted when component unmounts (modal closes)
}

const updateEnabled = () => {
  emit('update:enabled', localEnabled.value)
}

const updateShowBestMove = () => {
  emit('update:showBestMove', localShowBestMove.value)
}

const updateShowLines = () => {
  emit('update:showLines', parseInt(localShowLines.value))
}

const resetToDefaults = () => {
  localDepth.value = DEFAULT_DEPTH
  localShowBestMove.value = DEFAULT_SHOW_BEST_MOVE
  localShowLines.value = DEFAULT_SHOW_LINES
  // For reset, immediately emit all changes
  emit('update:depth', parseInt(localDepth.value))
  updateShowBestMove()
  updateShowLines()
  // Update original depth since we emitted it
  originalDepth.value = localDepth.value
}

// Emit depth changes when component is unmounted (modal closes)
onUnmounted(() => {
  if (localDepth.value !== originalDepth.value) {
    emit('update:depth', parseInt(localDepth.value))
  }
})

// Watch for prop changes
watch(() => props.depth, (newVal) => {
  localDepth.value = newVal
  originalDepth.value = newVal
})

watch(() => props.enabled, (newVal) => {
  localEnabled.value = newVal
})

watch(() => props.showBestMove, (newVal) => {
  localShowBestMove.value = newVal
})

watch(() => props.showLines, (newVal) => {
  localShowLines.value = newVal
})
</script>

<style scoped>
.evaluation-settings {
  background-color: transparent;
  border-radius: 0;
  padding: 0;
  margin: 0;
  border: none;
  min-width: 100%;
}

.settings-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.settings-title {
  color: #f2f2f2;
  margin-bottom: 12px;
  text-align: center;
  font-weight: 600;
  font-size: 16px;
}

.toggle-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #444;
  transition: .4s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #cdd26a;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

.toggle-label {
  color: #f2f2f2;
  font-size: 14px;
  font-weight: 600;
  min-width: 30px;
}

.setting-item {
  margin-bottom: 20px;
}

.setting-label {
  display: block;
  color: #f2f2f2;
  font-size: 14px;
  margin-bottom: 8px;
  font-weight: 500;
}

.setting-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #444;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.setting-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #cdd26a;
  cursor: pointer;
  border: 2px solid #aaa23a;
}

.setting-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #cdd26a;
  cursor: pointer;
  border: 2px solid #aaa23a;
}

.reset-btn {
  width: 100%;
  border-color: #f2f2f2;
  color: #f2f2f2;
  background-color: transparent;
  transition: color 0.15s ease-in-out, border-color 0.15s ease-in-out;
  font-size: 13px;
  padding: 8px 16px;
}

.reset-btn:hover {
  border-color: #cdd26a;
  color: #cdd26a;
  background-color: rgba(205, 210, 106, 0.1);
}
</style>
