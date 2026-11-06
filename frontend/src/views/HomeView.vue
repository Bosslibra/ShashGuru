<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import ChessBoard from '@/components/ChessBoard.vue'
import AIChat from '@/components/AIChat.vue'
import MoveTreeDisplay from '@/components/MoveTreeDisplay.vue'
import EngineLines from '@/components/EngineLines.vue'
import { useKeyboardNavigation } from '@/composables/useKeyboardNavigation'
import { useChatStore } from '@/stores/chat'
import { useGameStore } from '@/stores/game'

const game = useGameStore()
const {
  root: moveTree,
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

function switchTab(tab: 'moves' | 'chat') {
  activeTab.value = tab
}

useKeyboardNavigation(isLoading)
</script>

<template>
  <div id="chessboard" class="d-flex flex-column flex-lg-row justify-content-evenly m-2 m-lg-5" >
    <div class="flex-item mx-0 p-3 pt-0" :class="{ 'loading': isLoading }">
      <ChessBoard />
    </div>

    <div class="right-panel d-flex flex-column flex-lg-row flex-fill mx-2 mx-lg-5 gap-3">
      <!-- TABBED PANEL -->
      <div id="tabbed-panel" class="tabbed-section rounded-4 d-flex flex-column rounded-top-4 overflow-hidden">
        <!-- TAB NAVIGATION -->
        <div class="tab-navigation d-flex">
          <button 
            class="tab-button flex-fill py-2 px-3 border-0 fw-bold"
            :class="{ 'tab-active': activeTab === 'moves', 'tab-inactive': activeTab !== 'moves' }"
            @click="switchTab('moves')">
            <i class="material-icons me-1" style="font-size: 18px;">sports_esports</i>
            Moves
          </button>
          <button 
            class="tab-button flex-fill py-2 px-3 border-0 fw-bold"
            :class="{ 'tab-active': activeTab === 'chat', 'tab-inactive': activeTab !== 'chat' }"
            @click="switchTab('chat')">
            <i class="material-icons me-1" style="font-size: 18px;">chat</i>
            AI Chat
          </button>
        </div>

        <!-- TAB CONTENT -->
        <div class="tab-content flex-fill d-flex flex-column overflow-hidden">
          <!-- MOVES TAB -->
          <div class="tab-pane flex-fill d-flex flex-column overflow-hidden">
            <!-- PLAYER INFO -->
            <div v-if="hasPlayerInfo" id="playerInfo"
              class="d-flex align-items-center justify-content-between p-3 text-light"
              style="background-color: #33312e; border-bottom: 1px solid #ffffff1e; max-height: 100px;">

              <!-- White Player -->
              <div class="text-truncate text-center" style="flex: 1; padding-right: 1rem;">
                <div class="fw-bold fs-6">White:</div>
                <div class="fs-6 text-truncate">{{ whitePlayer }}</div>
              </div>

              <!-- Game Result  -->
              <div class="flex-shrink-0 mx-auto px-2">
                <div class="fs-4 fw-bold">{{ gameResult }}</div>
              </div>

              <!-- Black Player -->
              <div class="text-truncate text-center" style="flex: 1; padding-left: 1rem;">
                <div class="fw-bold fs-6">Black:</div>
                <div class="fs-6 text-truncate">{{ blackPlayer }}</div>
              </div>
            </div>
            
            <!-- MOVES -->
            <div v-if="activeTab === 'moves'" class="flex-fill">
              <div id="moveHeader" class="d-flex justify-content-center align-items-center py-1 flex-shrink-0">
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!canGoBack"
                    @click="game.goToStart">first_page</button>
                </div>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!canGoBack"
                    @click="game.back">arrow_back</button>
                </div>
                <span class="fs-6 fw-bold text-center mx-2">
                  <span v-if="isAnalysisMode" class="badge bg-warning text-dark ms-1">Analysis</span>
                </span>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!canGoForward"
                    @click="game.forward">arrow_forward</button>
                </div>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!canGoForward"
                    @click="game.goToEnd">last_page</button>
                </div>
                <div class="ms-1">
                  <button class="btn btn-sm" :class="isAnalysisMode ? 'btn-warning' : 'btn-outline-light'" 
                    @click="game.toggleAnalysisMode" title="Toggle Analysis Mode (Shift+Enter)">
                    <i class="material-icons" style="font-size: 18px;">analytics</i>
                  </button>
                </div>
                <div class="ms-1">
                  <button class="btn btn-sm btn-outline-info" 
                    @click="game.fetchMainLineEvaluations" 
                    :disabled="isLoadingEvaluations"
                    title="Fetch Evaluations">
                    <span v-if="isLoadingEvaluations" class="spinner-border spinner-border-sm me-1" role="status"></span>
                    <i class="material-icons" style="font-size: 18px;">assessment</i>
                  </button>
                </div>
              </div>
              <div class="flex-fill overflow-auto">
                <div id="moves" class="px-3 pt-3 pb-2 h-100">
                  <!-- Engine Lines Display -->
                  <EngineLines class="mb-3" />
                  <div v-if="hasMoves" class="move-tree shadow">
                    <div class="moves-header rounded-top ">
                      <span class="header-text fs-6">Moves</span>
                    </div> 
                      <div class="moves-body ps-2 rounded-bottom ">
                      <MoveTreeDisplay :node="moveTree" />
                    </div>
                  </div>
                  <div v-if="!hasMoves && !isAnalysisMode" class="text-secondary text-center">
                    Load a PGN or make moves on the board to begin analysis
                  </div>
                  <div v-if="!hasMoves && isAnalysisMode" class="text-secondary text-center">
                    <i class="material-icons me-2">info</i>Analysis mode enabled - make moves on the board or use arrow keys to navigate
                  </div>
                </div>
              </div>
            </div>

            <!-- CHAT TAB -->
            <div v-if="activeTab === 'chat'" id="chat-view" class="tab-pane chat-section flex-fill rounded-4 d-flex flex-column">
              <AIChat />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>



<style scoped>
.tabbed-section {
  background-color: #262421;
  min-width: 600px;
  height: 80vh;
  flex: 1;
}

.tab-navigation {
  background-color: #1a1916;
  border-bottom: 1px solid #3a3a3a;
  border-top-right-radius: 1em; 
  border-top-left-radius: 1em; 
}

.tab-button {
  background-color: transparent;
  color: #b2b2b2;
  transition: all 0.3s ease;
  
  border-bottom: 3px solid transparent !important;
}

.tab-button:hover {
  background-color: #2a2824;
  color: #e8e8e8;
}

.tab-active {
  background-color: #2f2d2a !important;
  color: #aaa23a !important;
  border-bottom: 3px solid #aaa23a !important;
  border-top-right-radius: 1em;
  border-top-left-radius: 1em;
  
}

.tab-inactive {
  background-color: #262421;
  border-top-right-radius: 1em;
  border-top-left-radius: 1em;
  border-bottom: 3px solid #262421 !important;

}

.tab-content {
  background-color: #262421;
}

.tab-pane {
  overflow: hidden;
}

.moves-section {
  background-color: #262421;
  min-width: 350px;
  max-width: 500px;
  height: 80vh;
  flex: 0 0 auto;
}

.chat-section {
  background-color: #262421;
  min-width: 400px;
  flex: 1;
}

.moves-header {
  background-color: #444;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
}

.header-text {
  color: #e8e8e8;
  font-weight: 600;
  font-size: 0.9rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  
}

.moves-body {
  border: 1px solid #444;
  border-top: 0px solid transparent;
  margin-bottom: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 60vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 8px 0;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

.right-panel {
  height: 80vh;
}

#chessboard {
  color: aliceblue;
  height: 50%;
}

.selected>.colorize {
  background-color: #cdd26a;
  color: black;
  border-radius: 4px;
  user-select: none;
}

.loading {
  pointer-events: none;
  /* Prevent all interaction */
}

#moves {
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  border-bottom: 1px solid #ffffff1e;
  line-height: 1.6;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

.move-tree {
  font-family: 'Courier New', monospace;
}

#moveHeader {
  background-color: #2f2d2a;
  border-bottom: 1px solid #ffffff1e;
}

#moveHeader button {
  border: none;
}

#playerInfo {
  background-color: #33312e;
  border-bottom: 1px solid #ffffff1e;
}

/* width */
::-webkit-scrollbar {
  width: 10px;
}

/* Track */
::-webkit-scrollbar-track {
  background: transparent;
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>