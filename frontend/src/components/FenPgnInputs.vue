<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTranslation } from 'i18next-vue'
import { CircleAlert } from '@lucide/vue'
import { InputGroup, InputGroupAddon, InputGroupInput, InputGroupText } from '@/components/ui/input-group'
import { isValidFen } from '@/lib/fen'
import { useGameStore } from '@/stores/game'
import { useToastStore } from '@/stores/toast'

const { t } = useTranslation()
const toast = useToastStore()
const game = useGameStore()

// The FEN box follows the board; typing a valid FEN starts a new analysis from that position.
const fenInput = ref(game.currentFen)
watch(
  () => game.currentFen,
  (fen) => (fenInput.value = fen),
)
watch(fenInput, (value) => {
  const fen = value.trim()
  if (fen && fen !== game.currentFen && isValidFen(fen)) game.loadFen(fen)
})

/** The typed FEN is not valid: say so instead of silently ignoring it. */
const fenInvalid = computed(() => {
  const fen = fenInput.value.trim()
  return !!fen && fen !== game.currentFen && !isValidFen(fen)
})

const pgnInput = ref(game.pgnText)
watch(
  () => game.pgnText,
  (text) => (pgnInput.value = text),
)

function loadPgn() {
  try {
    game.loadPgn(pgnInput.value)
  } catch (error) {
    console.warn(error)
    toast.error(t('errors.invalidPgn'))
  }
}
</script>

<template>
  <div class="mt-3 space-y-2">
    <div class="fen-input-container">
      <InputGroup>
        <InputGroupAddon>
          <InputGroupText class="num font-semibold">FEN</InputGroupText>
        </InputGroupAddon>
        <InputGroupInput
          id="fenInput"
          v-model="fenInput"
          class="num text-[13px]"
          :placeholder="t('board.fenPlaceholder')"
          autocomplete="off"
          :aria-label="t('board.fenLabel')"
          :aria-invalid="fenInvalid"
          :aria-describedby="fenInvalid ? 'fen-error' : undefined"
        />
      </InputGroup>
      <p v-if="fenInvalid" id="fen-error" class="mt-1 flex items-center gap-1 text-sm text-destructive" role="alert">
        <CircleAlert class="size-4" aria-hidden="true" />{{ t('errors.invalidFen') }}
      </p>
    </div>

    <div class="pgn-input-container">
      <InputGroup>
        <InputGroupAddon>
          <InputGroupText class="num font-semibold">PGN</InputGroupText>
        </InputGroupAddon>
        <InputGroupInput
          id="pgnInput"
          v-model="pgnInput"
          class="num text-[13px]"
          :placeholder="t('board.pgnPlaceholder')"
          autocomplete="off"
          :aria-label="t('board.pgnLabel')"
          @keyup.enter="loadPgn"
        />
      </InputGroup>
    </div>
  </div>
</template>
