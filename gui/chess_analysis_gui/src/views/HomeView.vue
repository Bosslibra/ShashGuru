<script setup>
import { ref } from 'vue';
import ChessBoard from '@/components/ChessBoard.vue'
import AIChat from '@/components/AIChat.vue';

const fen = ref(""); 

function updateFen(newFen) {
  fen.value = newFen; // Update parent state when ComponentA emits the new FEN
}

</script>

<template>
  <div class="d-flex justify-content-evenly mx-5 ">
    <div class="flex-item m-5 mt-2 p-3">
      <ChessBoard @updateFen="updateFen"></ChessBoard>
      
    </div>
    <div class="flex-item flex-fill m-5">
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