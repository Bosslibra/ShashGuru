<template>
  <div ref="rootEl" class="move-tree-display w-full">
    <!-- Moves in traditional notation, variations nested below -->
    <div class="moves-container w-full">
      <div v-for="(moveItem, index) in displayItems" :key="moveItem.id || index" class="move-item">
        <!-- Main move row -->
        <div v-if="moveItem.type === 'move-pair'" class="move-row grid grid-cols-[1.75rem_minmax(0,7.5rem)_minmax(0,7.5rem)] items-center gap-1 py-px">
          <span class="move-number num text-right text-xs font-semibold text-muted-foreground">{{ moveItem.moveNumber }}.</span>

          <template v-for="(node, side) in [moveItem.whiteMove, moveItem.blackMove]" :key="side">
            <button
              v-if="node"
              type="button"
              :data-move-id="node.id"
              aria-haspopup="menu"
              :aria-current="isSelectedMove(node) ? 'true' : undefined"
              :aria-label="moveLabel(node)"
              class="move-text num flex min-w-0 items-center gap-1 rounded-[calc(var(--radius)*0.6)] px-2 py-1 text-left text-[13px] outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring select-none [-webkit-touch-callout:none] touch-manipulation"
              :class="[
                side === 0 ? 'white-move' : 'black-move',
                isMainLineMove(node) ? 'main-line text-foreground' : 'variation italic text-muted-foreground',
                isSelectedMove(node) && 'current-move bg-lime! font-bold text-black!',
              ]"
              @click="game.goTo(node)"
            >
              <AnnotationIcon kind="shashin" :type="node.shashinType" />
              <AnnotationIcon kind="eval" :type="node.moveEvaluation" />
              <span>{{ node.move }}</span>
              <span
                v-if="!node.shashinType && node.evaluation"
                class="size-1 rounded-full bg-info/70"
                :title="t('moveTree.autoDetected')"
                aria-hidden="true"
              ></span>
            </button>
            <span v-else class="move-text empty px-2 py-1 text-muted-foreground/40" aria-hidden="true">...</span>
          </template>
        </div>

        <!-- Variation -->
        <div v-else-if="moveItem.type === 'variation'" class="variation-item my-1 ml-5">
          <div class="variation-line border-l-2 border-border bg-white/[0.02] py-1 pl-2">
            <MoveTreeDisplay :node="moveItem.variation" :level="level + 1" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useTranslation } from 'i18next-vue'
import AnnotationIcon from './AnnotationIcon.vue'
import type { MoveNode } from '@/lib/moveTree'
import { useGameStore } from '@/stores/game'

interface MovePairItem {
  type: 'move-pair'
  id: string
  moveNumber: number
  whiteMove: MoveNode | null
  blackMove: MoveNode | null
  isVariation?: undefined
}

interface VariationItem {
  type: 'variation'
  id: string
  variation: MoveNode
  isVariation: true
}

type DisplayItem = MovePairItem | VariationItem

const props = withDefaults(
  defineProps<{
    /** First node of the line displayed by this instance (the tree root, or a variation's first move). */
    node: MoveNode
    /** Nesting depth: 0 for the main tree. */
    level?: number
  }>(),
  { level: 0 },
)

const { t } = useTranslation()
const game = useGameStore()
const rootEl = ref<HTMLElement | null>(null)

// Moves and variations in display order
const displayItems = computed<DisplayItem[]>(() => {
  void game.version // the tree is mutated in place
  const items: DisplayItem[] = []
  buildDisplayItems(props.node, items, calculateStartingMoveIndex(props.node))
  return items
})

function calculateStartingMoveIndex(node: MoveNode): number {
  // White's first move is index 0, black's first move is index 1, ...
  if (!node.parent) return 0
  const fenParts = node.parent.fen.split(' ')
  if (fenParts.length < 6) return 0
  const fullMoveNumber = parseInt(fenParts[5]) || 1
  return (fullMoveNumber - 1) * 2 + (fenParts[1] === 'w' ? 0 : 1)
}

function variationsOf(node: MoveNode): VariationItem[] {
  return node.children
    .filter((child) => child !== node.mainLine)
    .map((variation) => ({ type: 'variation', id: `var-${variation.id}`, variation, isVariation: true }))
}

function buildDisplayItems(startNode: MoveNode, items: DisplayItem[], moveIndex: number) {
  let current: MoveNode | null = startNode
  let index = moveIndex

  // Skip the root node: it has no move
  if (!current.move) current = current.mainLine ?? current.children[0] ?? null

  while (current && current.move) {
    const moveNumber = Math.floor(index / 2) + 1

    if (index % 2 === 0) {
      // A white move, paired with the black reply
      const blackMove: MoveNode | null = current.mainLine
      items.push({ type: 'move-pair', id: `pair-${moveNumber}`, moveNumber, whiteMove: current, blackMove })
      items.push(...variationsOf(current))
      if (blackMove) items.push(...variationsOf(blackMove))
      current = blackMove?.mainLine ?? null
      index += blackMove ? 2 : 1
    } else {
      // A black move starting a variation
      items.push({ type: 'move-pair', id: `pair-${moveNumber}`, moveNumber, whiteMove: null, blackMove: current })
      items.push(...variationsOf(current))
      current = current.mainLine
      index += 1
    }
  }
}

function isSelectedMove(moveNode: MoveNode | null): boolean {
  return !!moveNode && game.currentNode.id === moveNode.id
}

function isMainLineMove(moveNode: MoveNode | null): boolean {
  if (!moveNode || !moveNode.parent) return true
  return moveNode.parent.mainLine === moveNode
}

/** Text read by screen readers for a move: SAN plus its annotations (the icons are decorative). */
function moveLabel(node: MoveNode): string {
  const parts: string[] = [node.move ?? '']
  if (node.moveEvaluation) parts.push(t(`moveTree.eval.${node.moveEvaluation}` as never))
  if (node.shashinType) parts.push(t(`moveTree.shashin.${node.shashinType}` as never))
  return parts.join(', ')
}

// Keep the current move visible while navigating (only the root instance, which contains all moves)
watch(
  () => game.currentNode.id,
  async () => {
    if (props.level !== 0) return
    await nextTick()
    rootEl.value?.querySelector('.current-move')?.scrollIntoView({ block: 'nearest' })
  },
)
</script>
