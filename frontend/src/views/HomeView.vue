<script setup>
import { ref } from 'vue';
import ChessBoard from '@/components/ChessBoard.vue'
import AIChat from '@/components/AIChat.vue';
import { Chess } from 'chess.js'

const fen = ref("");
const moves = ref([])

function updateFen(newFen) {
  fen.value = newFen; // Update parent state when ComponentA emits the new FEN
}

function setMovesFromPGN(history) {
  moves.value = history;
}

// NEW THINGS FOR PGN history
const selectedMoveIndex = ref(-1);

function onMoveClicked(index) {
  selectedMoveIndex.value = index;
  const chess = new Chess();
  for(let i = 0; i <= index; i++) {
    chess.move(moves.value[i]);
  }
  updateFen(chess.fen());
}




</script>

<template>
  <div class="d-flex justify-content-evenly mx-5 ">
    <div class="flex-item m-5 mt-2 p-3">
      <ChessBoard :fenProp="fen" @updateFen="updateFen" @setMovesFromPGN="setMovesFromPGN"></ChessBoard>

    </div>
    <div id="chat-view" class="flex-item flex-fill m-5 rounded-4">

      <!-- MOVES -->
      <div class="p-4 fs-5 border-bottom">
        <h5>Moves</h5>
        <span
          :class="{ selected: index === selectedMoveIndex }" 
          @click="onMoveClicked(index)"
          style="cursor:pointer;" v-for="(move, index) in moves" :key="index">
          
          <span class="" v-if="index % 2 === 0">
            {{ Math.floor(index / 2 + 1) }}.
            
          </span>
          <span class="colorize px-2 p-1" v-if="index % 2 === 0">
          {{ move }}
          </span>
          <span class="colorize px-2 p-1 me-3" v-else>
          {{ move }}
          </span>
        </span>
      </div>

      <!--CHAT-->

      <AIChat :fen="fen"></AIChat>
    </div>
  </div>
</template>


<style scoped>
#chat-view {
    background-color: #262421;
}
.d-flex {
  color: aliceblue;
  height: 50%;
}
.selected > .colorize {
  background-color: #cdd26a;
  color: black;
  border-radius: 4px;
  user-select: none;
}
</style>