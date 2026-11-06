<template>
  <div class="evaluation-container flex h-full flex-col items-center gap-1">
    <div
      class="relative w-7 flex-1 overflow-hidden rounded-(--radius) border border-border bg-surface-nav sm:w-9"
      :class="{ 'opacity-50': !enabled, 'opacity-60': loading && enabled }"
    >
      <div class="evaluation-bar relative flex h-full w-full flex-col-reverse">
        <template v-if="enabled">
          <!-- First child sits at the bottom (flex-col-reverse): the side that is at the bottom of the board -->
          <div
            class="eval-section flex items-center justify-center transition-[height] duration-300"
            :class="boardOrientation !== 'white' ? 'bg-linear-to-b from-[#1a1a1a] to-[#333]' : 'bg-linear-to-t from-[#f0f0f0] to-[#d0d0d0]'"
            :style="{ height: (boardOrientation !== 'white' ? blackPercentage : whitePercentage) + '%' }"
          >
            <div
              v-if="(boardOrientation !== 'white' ? blackPercentage : whitePercentage) > 15"
              class="num rotate-180 text-[10px] font-bold [writing-mode:vertical-lr]"
              :class="boardOrientation !== 'white' ? 'text-white' : 'text-black'"
            >
              {{ formatEvaluation() }}
            </div>
          </div>

          <div
            class="eval-section flex items-center justify-center transition-[height] duration-300"
            :class="boardOrientation !== 'white' ? 'bg-linear-to-t from-[#f0f0f0] to-[#d0d0d0]' : 'bg-linear-to-b from-[#1a1a1a] to-[#333]'"
            :style="{ height: (boardOrientation !== 'white' ? whitePercentage : blackPercentage) + '%' }"
          >
            <div
              v-if="(boardOrientation !== 'white' ? whitePercentage : blackPercentage) > 15"
              class="num rotate-180 text-[10px] font-bold [writing-mode:vertical-lr]"
              :class="boardOrientation !== 'white' ? 'text-black' : 'text-white'"
            >
              {{ formatEvaluation() }}
            </div>
          </div>
        </template>

        <template v-else>
          <div class="h-1/2 bg-linear-to-b from-[#1a1a1a] to-[#333]"></div>
          <div class="h-1/2 bg-linear-to-t from-[#f0f0f0] to-[#d0d0d0]"></div>
        </template>
      </div>

      <!-- Center line -->
      <div class="absolute inset-x-0 top-1/2 z-10 h-0.5 -translate-y-1/2 bg-[#666]"></div>

      <div v-if="loading && enabled" class="absolute inset-0 z-20 grid place-items-center bg-black/20">
        <Spinner class="size-4 text-lime" />
      </div>

      <div v-if="!enabled" class="absolute inset-0 z-20 grid place-items-center bg-black/30">
        <span class="text-[11px] font-bold tracking-wider text-muted-foreground [writing-mode:vertical-lr]">
          {{ t('common.off') }}
        </span>
      </div>
    </div>

    <!-- Evaluation error: focusable icon with a tooltip -->
    <Tooltip v-if="error && enabled">
      <TooltipTrigger as-child>
        <button
          type="button"
          class="rounded-full p-0.5 text-destructive outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="t('engine.failed')"
        >
          <CircleAlert class="size-5" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">{{ t('engine.failed') }}</TooltipContent>
    </Tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useTranslation } from 'i18next-vue'
import { CircleAlert } from '@lucide/vue'
import { Spinner } from '@/components/ui/spinner'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { formatScore, scoreToPercent } from '@/lib/evalFormat'
import { useEvaluationStore } from '@/stores/evaluation'
import { useSettingsStore } from '@/stores/settings'

const { t } = useTranslation()

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
