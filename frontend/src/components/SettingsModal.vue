<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import EvaluationSettings from './EvaluationSettings.vue'

const emit = defineEmits<{ close: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="settings-modal-overlay" @click="emit('close')">
    <div class="settings-modal" @click.stop>
      <div class="settings-modal-header">
        <h5 class="modal-title">Evaluation Settings</h5>
        <button @click="emit('close')" class="close-btn material-icons">close</button>
      </div>
      <div class="settings-modal-body">
        <EvaluationSettings />
      </div>
    </div>
  </div>
</template>

<style scoped>
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
</style>
