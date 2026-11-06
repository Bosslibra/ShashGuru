<script setup lang="ts">
// DEV ONLY: loaded behind import.meta.env.DEV (see App.vue), never part of the production build.
import { onMounted, onUnmounted, ref } from 'vue'
import { DIRECTIONS, getDirection, setDirection, type DirectionId } from './direction'

const current = ref<DirectionId>(getDirection())
const minimized = ref(false)

function choose(id: DirectionId) {
  setDirection(id)
  current.value = id
}

/** Alt+D cycles through the directions. */
function onKeydown(event: KeyboardEvent) {
  if (!event.altKey || event.key.toLowerCase() !== 'd') return
  event.preventDefault()
  const index = DIRECTIONS.findIndex((d) => d.id === current.value)
  choose(DIRECTIONS[(index + 1) % DIRECTIONS.length].id)
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div
    class="fixed bottom-3 right-3 z-[3000] flex items-center gap-1 rounded-full border border-lime/40 bg-black/85 p-1 pl-3 text-xs text-white shadow-xl backdrop-blur"
    role="group"
    aria-label="Visual direction (dev only)"
  >
    <span class="mr-1 font-mono uppercase tracking-wider text-lime">dev · ui</span>
    <template v-if="!minimized">
      <button
        v-for="d in DIRECTIONS"
        :key="d.id"
        type="button"
        class="rounded-full px-3 py-1 font-medium transition-colors"
        :class="current === d.id ? 'bg-lime text-black' : 'text-white/80 hover:bg-white/10'"
        :aria-pressed="current === d.id"
        @click="choose(d.id)"
      >
        {{ d.label }}
      </button>
    </template>
    <button
      type="button"
      class="rounded-full px-2 py-1 text-white/60 hover:bg-white/10"
      :aria-label="minimized ? 'Expand switcher' : 'Minimize switcher'"
      :title="'Alt+D cycles directions'"
      @click="minimized = !minimized"
    >
      {{ minimized ? '▸' : '◂' }}
    </button>
  </div>
</template>
