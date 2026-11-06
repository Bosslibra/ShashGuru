<script setup lang="ts">
/**
 * The move list panel: the recursive MoveTreeDisplay inside ONE context menu.
 * The menu applies to whichever move was pressed (found through its data-move-id), with a right
 * click, the Menu key / Shift+F10 on a focused move, or a long press on touch.
 */
import { computed, nextTick, ref, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useTranslation } from 'i18next-vue'
import { ArrowUpToLine, Plus, Trash2, X } from '@lucide/vue'
import AnnotationIcon from './AnnotationIcon.vue'
import MoveTreeDisplay from './MoveTreeDisplay.vue'
import { Button } from '@/components/ui/button'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Input } from '@/components/ui/input'
import { MOVE_EVALUATION_TYPES, SHASHIN_GROUPS } from '@/lib/annotations'
import type { MoveNode } from '@/lib/moveTree'
import { useGameStore } from '@/stores/game'

const { t } = useTranslation()
const game = useGameStore()
const { root: moveTree, analysisMode } = storeToRefs(game)

/** Translation by dynamic key (the keys are checked in the locale files, not here). */
const tk = (key: string): string => t(key as never)

const selected = shallowRef<MoveNode | null>(null)
let trigger: HTMLElement | null = null

function findNode(id: string): MoveNode | null {
  const stack: MoveNode[] = [game.root]
  while (stack.length) {
    const node = stack.pop()!
    if (node.id === id) return node
    stack.push(...node.children)
  }
  return null
}

/** Remember which move the menu is about, before the menu opens. */
function selectFromEvent(event: Event): MoveNode | null {
  const el = (event.target as HTMLElement | null)?.closest<HTMLElement>('[data-move-id]')
  const node = el?.dataset.moveId ? findNode(el.dataset.moveId) : null
  if (node && el) {
    selected.value = node
    trigger = el
  }
  return node
}

function onContextMenuCapture(event: MouseEvent) {
  // Not on a move: keep the menu closed and let the browser show its own
  if (!selectFromEvent(event)) event.stopImmediatePropagation()
}

function onPointerDownCapture(event: PointerEvent) {
  if (event.pointerType !== 'mouse') selectFromEvent(event) // long press on touch
}

/** After closing, focus the move the menu was about instead of the whole list. */
function onCloseAutoFocus(event: Event) {
  event.preventDefault()
  trigger?.focus()
}

// A variation can be promoted unless it already is on the main line
const canPromote = computed(() => !!selected.value?.parent && !selected.value.isOnMainLinePath())
// The root (the node with no move) cannot be deleted
const canDelete = computed(() => !!selected.value?.move)

function promote() {
  if (selected.value && canPromote.value) game.promote(selected.value)
}
function remove() {
  if (selected.value && canDelete.value) game.remove(selected.value)
}
function setEvaluation(type: string | null) {
  if (selected.value) game.setMoveEvaluation(selected.value, type)
}
function setShashin(type: string | null) {
  if (selected.value) game.setShashinType(selected.value, type)
}

// Analysis mode: add a move by typing it
const newMove = ref('')
const moveInput = ref<{ $el: HTMLInputElement } | null>(null)

function handleAddMove() {
  const text = newMove.value.trim()
  if (!text) return
  game.play(text)
  newMove.value = ''
}

// Focus the "add move" box when analysis mode is switched on
watch(
  analysisMode,
  async (on) => {
    if (!on) return
    await nextTick()
    moveInput.value?.$el?.focus()
  },
  { immediate: true },
)
</script>

<template>
  <section class="move-tree panel font-mono">
    <header class="panel-header">
      <h3 class="panel-label">{{ t('home.movesHeader') }}</h3>
    </header>

    <ContextMenu>
      <ContextMenuTrigger as-child>
        <div
          id="moves-list"
          class="moves-body p-(--pad-sm)"
          @contextmenu.capture="onContextMenuCapture"
          @pointerdown.capture="onPointerDownCapture"
        >
          <MoveTreeDisplay :node="moveTree" />
        </div>
      </ContextMenuTrigger>

      <ContextMenuContent class="w-60" @close-auto-focus="onCloseAutoFocus">
        <ContextMenuLabel class="panel-label">{{ t('moveTree.menu.title') }}</ContextMenuLabel>

        <ContextMenuItem v-if="canPromote" @select="promote">
          <ArrowUpToLine class="text-lime" aria-hidden="true" />{{ t('moveTree.menu.promote') }}
        </ContextMenuItem>
        <ContextMenuItem v-if="canDelete" variant="destructive" @select="remove">
          <Trash2 aria-hidden="true" />{{ t('moveTree.menu.delete') }}
        </ContextMenuItem>
        <ContextMenuSeparator v-if="canPromote || canDelete" />

        <!-- Move quality -->
        <ContextMenuSub>
          <ContextMenuSubTrigger>{{ t('moveTree.menu.moveEvaluation') }}</ContextMenuSubTrigger>
          <ContextMenuSubContent class="w-52">
            <ContextMenuItem v-for="type in MOVE_EVALUATION_TYPES" :key="type" @select="setEvaluation(type)">
              <AnnotationIcon kind="eval" :type="type" />{{ tk(`moveTree.eval.${type}`) }}
            </ContextMenuItem>
            <ContextMenuSeparator />
            <ContextMenuItem @select="setEvaluation(null)">
              <X class="text-muted-foreground" aria-hidden="true" />{{ t('moveTree.menu.clearEvaluation') }}
            </ContextMenuItem>
          </ContextMenuSubContent>
        </ContextMenuSub>

        <!-- Shashin position type -->
        <ContextMenuSub>
          <ContextMenuSubTrigger>{{ t('moveTree.menu.shashinType') }}</ContextMenuSubTrigger>
          <ContextMenuSubContent class="max-h-[min(70vh,28rem)] w-56 overflow-y-auto">
            <template v-for="(group, index) in SHASHIN_GROUPS" :key="group.key">
              <ContextMenuSeparator v-if="index > 0" />
              <ContextMenuLabel class="panel-label">{{ tk(`moveTree.menu.groups.${group.key}`) }}</ContextMenuLabel>
              <ContextMenuItem v-for="type in group.types" :key="type" @select="setShashin(type)">
                <AnnotationIcon kind="shashin" :type="type" />{{ tk(`moveTree.shashin.${type}`) }}
              </ContextMenuItem>
            </template>
            <ContextMenuSeparator />
            <ContextMenuItem @select="setShashin(null)">
              <X class="text-muted-foreground" aria-hidden="true" />{{ t('moveTree.menu.clearShashin') }}
            </ContextMenuItem>
          </ContextMenuSubContent>
        </ContextMenuSub>
      </ContextMenuContent>
    </ContextMenu>

    <!-- Analysis mode: type a move to add it -->
    <div v-if="analysisMode" class="flex items-center gap-2 border-t border-(--panel-divider) p-(--pad-sm)">
      <Input
        ref="moveInput"
        v-model="newMove"
        class="num h-8 max-w-64 text-[13px]"
        :placeholder="t('moveTree.addMovePlaceholder')"
        :aria-label="t('moveTree.addMove')"
        autocomplete="off"
        @keyup.enter="handleAddMove"
        @keyup.esc="newMove = ''"
      />
      <Button variant="outline" size="icon-sm" :aria-label="t('moveTree.addMove')" @click="handleAddMove">
        <Plus aria-hidden="true" />
      </Button>
    </div>
  </section>
</template>
