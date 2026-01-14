<script setup>
import { useDGT } from "@/services/useDGT";
import { onUnmounted, ref, watch } from "vue";
import { Chess } from "chess.js";

// Define the emit
const emit = defineEmits(["update:fen"]);
//const chess = new Chess();
const {
    active,
    lastMove,
    moves,
    position,
    //clock,
    //match,
    connect,
    disconnect,
    setup,
    //flip,
} = useDGT();

// Track which board feedId we want to control (for now assume first = 1)
const selectedFeedId = ref(1);

// Example FEN for setup
const fenInput = ref("startpos"); // can replace with real FEN

// Track full FEN locally
/*
const moveNumber = ref(1);
const whoShouldMove = ref('w'); // start with white to move
*/
const moveInProgress = ref(false);
const isConnecting = ref(false);
const startFen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"; // previous piece placement
const fenHistory = ref([])

function cleanup() {
    fenHistory.value = []
}

function reconstructFen() {
    console.log("Moves", moves.value)
    console.log("lastmove", lastMove.value)
    const game = (fenHistory.value && fenHistory.value.length > 0)
        ? new Chess(fenHistory.value[fenHistory.value.length - 1])
        : new Chess(startFen);

    if (lastMove.value) {
        const result = game.move(lastMove.value);
        if (!result) {
            console.warn(`Invalid move: ${lastMove.value}`);
        }}
    return game.fen();
}
const toggleConnection = () => {
    if (active.value) {
        disconnect();
        cleanup();
    } else {
        console.log("Connecting...")
        connect();
        console.log("Connected.\nSetting up...")
        isConnecting.value = true;
        setTimeout(() => {
            setupBoard()
            isConnecting.value = false;
        }, 100)
    }
};

// Call setup for SAN reconstruction
const setupBoard = () => {
    if (fenInput.value === "startpos") {
        setup(
            selectedFeedId.value,
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        );
    } else {
        setup(selectedFeedId.value, fenInput.value);
    }
};


// Emit best-effort FEN on board change
watch(position, (newBoard) => {
    if (!newBoard) return;
    
    fenHistory.value.push(reconstructFen())
    emit("update:fen", fenHistory.value[fenHistory.value.length - 1]);

});

onUnmounted(() => {
    disconnect();
    cleanup();
});
</script>


<template>
    <button class="btn btn-sm m-1" @click="toggleConnection"
        :style="active ? 'background-color: #aa23a; !important' : ''">
        Use DGT e-Board
        <span v-if="isConnecting" class="activity-dot bg-warning"></span>
        <span v-else-if="active" class="activity-dot active"></span>
        <span v-else class="activity-dot bg-danger"></span>
    </button>
</template>

<style scoped>
button.btn {
    background: #262421;
    color: #f2f2f2;
    border: none;
    font-weight: 600;
    border-radius: 6px;
    padding: 0.5em 1.2em;
    transition: background 0.2s, color 0.2s, box-shadow 0.2s;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}

.activity-dot {
    width: .8em;
    height: .8em;
    border-radius: 50%;
    display: inline-block;
    margin-left: 5px;
}

.active {
    background-color: green;
}

.inactive {
    background-color: red;
}
</style>