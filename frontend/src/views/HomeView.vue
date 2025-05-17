<script setup>
import { ref } from 'vue';
import ChessBoard from '@/components/ChessBoard.vue'
import AIChat from '@/components/AIChat.vue';

const fen = ref(""); 
const moves = ref([])

function updateFen(newFen) {
  fen.value = newFen; // Update parent state when ComponentA emits the new FEN
}

function showMoveHistory(history){
  moves.value = history;
}




</script>

<template>
  <div class="d-flex justify-content-evenly mx-5 ">
    <div class="flex-item m-5 mt-2 p-3">
      <ChessBoard @updateFen="updateFen" @showMoveHistory="showMoveHistory"></ChessBoard>
      
    </div>
    <div class="flex-item flex-fill m-5">
      <div>
        <span class="p-1" v-for="(move, index) in moves" :key="index">
          <span class="ps-2" v-if="index %2 === 0">
            {{ Math.floor(index/2 +1) }}.
          </span>
          {{ move }}
        </span>
      </div>
      <AIChat :fen="fen"></AIChat>
    </div>
  </div>
</template>


<style>
  .d-flex {
    color: aliceblue;
    height: 50%;
  }
</style>