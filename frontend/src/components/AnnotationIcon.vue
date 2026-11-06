<script setup lang="ts">
/** Decorative icon for a move annotation (quality or Shashin type). Meaning is given by the parent's label. */
import { computed } from 'vue'
import { SHASHIN_LEVEL_ICONS, moveEvaluationMeta, shashinMeta } from '@/lib/annotations'

const props = defineProps<{
  kind: 'eval' | 'shashin'
  type?: string | null
}>()

const meta = computed(() => (props.kind === 'eval' ? moveEvaluationMeta(props.type) : shashinMeta(props.type)))
const level = computed(() => {
  if (props.kind !== 'shashin') return null
  const lvl = shashinMeta(props.type)?.level
  return lvl ? (SHASHIN_LEVEL_ICONS[lvl] ?? null) : null
})
</script>

<template>
  <span v-if="meta" class="inline-flex shrink-0 items-center" :class="meta.color" aria-hidden="true">
    <component :is="meta.icon" class="size-3.5" />
    <component :is="level" v-if="level" class="-ml-0.5 size-3 opacity-80" />
  </span>
</template>
