<script setup>
import { useDGT } from "@/services/useDGT";
import { onUnmounted, ref, watch } from "vue";
//import { Chess } from "chess.js";

// Define the emit
const emit = defineEmits(["update:fen"]);
const startpos = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
//const chess = new Chess();
const {
    active,
    //lastMove,
    //moves,
    position,
    //clock,
    //match,
    connect,
    disconnect,
    //setup,
    //flip,
} = useDGT();
/*
// Track which board feedId we want to control (for now assume first = 1)
const selectedFeedId = ref(1);

// Example FEN for setup
const fenInput = ref("startpos"); // can replace with real FEN
*/
// Track full FEN locally
const moveNumber = ref(1);
const isWhite = ref(true); // start with white to move
let lastBoard = ""; // previous piece placement


const toggleConnection = () => {
    if (active.value) {
        disconnect();
    } else {
        connect();
    }
};
/*
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

// Flip board orientation
const flipBoard = () => {
    flip(selectedFeedId.value, true);
};
*/

/**
 * Determine who played the last move based on board positions
 * Handles normal moves, captures, castling, and promotions.
 * @param {string} oldBoard - previous board string
 * @param {string} newBoard - current board string
 * @returns {'w' | 'b'} - 'w' if white moved, 'b' if black moved
 */
const detectLastPlayer = (oldBoard, newBoard) => {
    if (!oldBoard || !newBoard) {
        if (newBoard.trim() === startpos.trim()) {
            return "b" // we fake that black has played last when starting position
        }
        else {
            return null
        }
    }

    const oldRows = oldBoard.split('/');
    const newRows = newBoard.split('/');

    // Track moved pieces
    const movedPieces = [];

    for (let r = 0; r < 8; r++) {
        const oldRow = expandFENRow(oldRows[r]);
        const newRow = expandFENRow(newRows[r]);

        for (let c = 0; c < 8; c++) {
            if (oldRow[c] !== newRow[c]) {
                // If a piece disappeared or appeared, record it
                if (oldRow[c] !== '.') movedPieces.push(oldRow[c]);
                if (newRow[c] !== '.') movedPieces.push(newRow[c]);
            }
        }
    }

    // Decide based on the first moved piece (normal moves or captures)
    for (const p of movedPieces) {
        if (p >= 'A' && p <= 'Z') return 'w';
        if (p >= 'a' && p <= 'z') return 'b';
    }

    // Fallback, shouldn't happen in normal moves
    return null;
};


/**
 * Expand a FEN row string into 8 characters
 * 'rnbqkbnr' -> 'rnbqkbnr'
 * 'pppppppp' -> 'pppppppp'
 * '8' -> '........'
 */
const expandFENRow = (row) => {
    let expanded = '';
    for (const ch of row) {
        if (ch >= '1' && ch <= '8') {
            expanded += '.'.repeat(Number(ch));
        } else {
            expanded += ch;
        }
    }
    return expanded;
};



// Emit best-effort FEN on board change
watch(position, (newBoard) => {
    if (!newBoard) return;

    const player = detectLastPlayer(lastBoard, newBoard);
    console.log("Last move played by:", player);
    // Only increment move number after black moves
    if (player === 'b') moveNumber.value += 1;
    const colorToMove = player === 'w' ? 'b': 'w'; // player indicates who has played last, so we invert it for who has to play next
    const fullFEN = `${newBoard} ${colorToMove} KQkq - 0 ${moveNumber.value}`; 

    // Toggle color for next change
    isWhite.value = !isWhite.value;
    lastBoard = newBoard;

    emit("update:fen", fullFEN);
});

onUnmounted(() => {
    disconnect();
});
</script>


<template>
    <button class="btn btn-sm m-1" @click="toggleConnection"
        :style="active ? 'background-color: #aa23a; !important' : ''">
        Use DGT e-Board
        <span class="activity-dot" :class="active ? 'active':'bg-danger'"></span>
    </button>
    <!--
    <div v-if="active">
      <div>
        <label>FEN:</label>
        <input v-model="fenInput" placeholder="Enter FEN" />
        <button @click="setupBoard">Setup</button>
      </div>

      <div>
        <button @click="flipBoard">Flip Board</button>
      </div>

      <div>
        <strong>Latest move:</strong> {{ lastMove }}
      </div>

      <div>
        <strong>Move list:</strong>
        <span v-if="moves.length === 0">[none yet]</span>
        <ul>
          <li v-for="(m, i) in moves" :key="i">{{ i + 1 }}. {{ m }}</li>
        </ul>
      </div>

      <div>
        <strong>Board FEN:</strong> {{ position }}
      </div>

      <div>
        <strong>Clock:</strong> {{ clock }}
      </div>

      <div>
        <strong>Match:</strong>
        <span :style="{ color: match ? 'green' : 'red' }">{{ match }}</span>
      </div>
    </div>
    -->

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