<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useTranslation } from 'i18next-vue'
import {
  ChartNoAxesColumn,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Info,
  ListOrdered,
  MessageSquare,
  Microscope,
} from '@lucide/vue'
import AIChat from '@/components/AIChat.vue'
import ChessBoard from '@/components/ChessBoard.vue'
import EngineLines from '@/components/EngineLines.vue'
import IconButton from '@/components/IconButton.vue'
import MoveTreePanel from '@/components/MoveTreePanel.vue'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia } from '@/components/ui/empty'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Spinner } from '@/components/ui/spinner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useKeyboardNavigation } from '@/composables/useKeyboardNavigation'
import { useChatStore } from '@/stores/chat'
import { useGameStore } from '@/stores/game'

const { t } = useTranslation()
const game = useGameStore()
const {
  hasMoves,
  hasPlayerInfo,
  whitePlayer,
  blackPlayer,
  gameResult,
  canGoBack,
  canGoForward,
  analysisMode: isAnalysisMode,
  loadingEvaluations: isLoadingEvaluations,
} = storeToRefs(game)
const { loading: isLoading } = storeToRefs(useChatStore())

const activeTab = ref<'moves' | 'chat'>('moves')

/** The tabs handle the arrow keys themselves: keep the global move navigation from also firing. */
function onTabsKeydown(event: KeyboardEvent) {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) event.stopPropagation()
}

useKeyboardNavigation(isLoading)
</script>

<template>
  <main
    id="chessboard"
    class="home-layout mx-auto grid max-w-[1800px] grid-cols-1 gap-(--gap) p-(--pad) text-foreground lg:grid-cols-[clamp(320px,calc(70vmin_+_80px),780px)_minmax(360px,1fr)] lg:items-start"
  >
    <div class="board-col min-w-0" :class="{ 'pointer-events-none cursor-progress opacity-70': isLoading }">
      <ChessBoard />
    </div>

    <!-- Tabbed panel -->
    <section id="tabbed-panel" class="tabbed-section panel panel-fill flex min-w-0 flex-col">
      <Tabs v-model="activeTab" class="flex min-h-0 flex-1 flex-col gap-0">
        <TabsList variant="line" class="w-full shrink-0" :aria-label="t('home.tabs.label')" @keydown="onTabsKeydown">
          <TabsTrigger value="moves">
            <ListOrdered aria-hidden="true" />{{ t('home.tabs.moves') }}
          </TabsTrigger>
          <TabsTrigger value="chat">
            <MessageSquare aria-hidden="true" />{{ t('home.tabs.chat') }}
          </TabsTrigger>
        </TabsList>

        <!-- Player info -->
        <div
          v-if="hasPlayerInfo"
          id="playerInfo"
          class="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-(--panel-divider) bg-black/20 px-(--pad) py-(--pad-sm) text-center"
        >
          <div class="min-w-0">
            <div class="panel-label">{{ t('home.whiteLabel') }}</div>
            <div class="truncate text-sm font-medium">{{ whitePlayer }}</div>
          </div>
          <div class="num text-xl font-bold text-lime">{{ gameResult }}</div>
          <div class="min-w-0">
            <div class="panel-label">{{ t('home.blackLabel') }}</div>
            <div class="truncate text-sm font-medium">{{ blackPlayer }}</div>
          </div>
        </div>

        <!-- Moves tab -->
        <TabsContent value="moves" id="moves-panel" class="flex min-h-0 flex-1 flex-col">
          <div
            id="moveHeader"
            class="flex shrink-0 flex-wrap items-center justify-center gap-1 border-b border-(--panel-divider) bg-black/15 px-2 py-1.5"
          >
            <IconButton :label="t('home.toolbar.first')" :disabled="!canGoBack" @click="game.goToStart()">
              <ChevronsLeft aria-hidden="true" />
            </IconButton>
            <IconButton :label="t('home.toolbar.back')" :disabled="!canGoBack" @click="game.back()">
              <ChevronLeft aria-hidden="true" />
            </IconButton>
            <span v-if="isAnalysisMode" class="eval-chip mx-1 text-warning">{{ t('home.analysisBadge') }}</span>
            <IconButton :label="t('home.toolbar.forward')" :disabled="!canGoForward" @click="game.forward()">
              <ChevronRight aria-hidden="true" />
            </IconButton>
            <IconButton :label="t('home.toolbar.last')" :disabled="!canGoForward" @click="game.goToEnd()">
              <ChevronsRight aria-hidden="true" />
            </IconButton>

            <Separator orientation="vertical" class="mx-1 h-5" />

            <IconButton
              :label="t('home.toolbar.toggleAnalysis')"
              shortcut="Shift+Enter"
              :variant="isAnalysisMode ? 'default' : 'outline'"
              :pressed="isAnalysisMode"
              @click="game.toggleAnalysisMode()"
            >
              <Microscope aria-hidden="true" />
            </IconButton>
            <IconButton
              :label="t('home.toolbar.fetchEvaluations')"
              variant="outline"
              :disabled="isLoadingEvaluations"
              @click="game.fetchMainLineEvaluations()"
            >
              <Spinner v-if="isLoadingEvaluations" aria-hidden="true" />
              <ChartNoAxesColumn v-else aria-hidden="true" />
            </IconButton>
          </div>

          <ScrollArea class="min-h-0 flex-1">
            <div id="moves" class="flex flex-col gap-(--gap) p-(--pad)">
              <EngineLines />
              <MoveTreePanel v-if="hasMoves" />
              <Empty v-else class="border border-dashed border-border">
                <EmptyHeader>
                  <EmptyMedia variant="icon"><Info aria-hidden="true" /></EmptyMedia>
                  <EmptyDescription>
                    {{ isAnalysisMode ? t('home.emptyAnalysis') : t('home.emptyMoves') }}
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            </div>
          </ScrollArea>
        </TabsContent>

        <!-- Chat tab -->
        <TabsContent value="chat" id="chat-view" class="min-h-0 flex-1">
          <AIChat />
        </TabsContent>
      </Tabs>
    </section>
  </main>
</template>
