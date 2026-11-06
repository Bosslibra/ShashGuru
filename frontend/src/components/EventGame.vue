<template>
    <div id="eventGameCard" class="rounded m-3 p-2" style="" @click="navigateToAnalysis">

        <!-- Black Player -->
        <div id="blackPlayer" class="d-flex justify-content-between align-items-center">
            <div v-if="metadata.blackPlayerTitle" class="flex-shrink-0">
                <span class="title ps-1">{{ metadata.blackPlayerTitle }}</span>
            </div>
            <div class="text-truncate px-1 flex-shrink-1">
                {{ metadata.blackPlayerName }}
            </div>
            <div v-if="metadata.blackPlayerRating" class="flex-item flex-grow-1 text-start">
                ({{ metadata.blackPlayerRating }})
            </div>
            <div v-if="resultFor('black')" class="flex-shrink-0">
                <span :class="['ms-3 pe-1 fw-bold fs-6', resultClass(resultFor('black'))]">
                    {{ resultFor('black') }}
                </span>
            </div>
        </div>

        <!-- Board -->
        <div class="position-relative d-flex justify-content-center" style="height:250px; width:250px;">
            <TheChessboard :board-config="boardConfig"
                style="height:250px; width:250px;" />


            <div v-if="metadata.gameResult === '*'" class="overlay d-flex justify-content-center align-items-center">
                Ongoing
            </div>
        </div>

        <!-- White Player -->
        <div id="whitePlayer" class="d-flex justify-content-between align-items-center">
            <div v-if="metadata.whitePlayerTitle" class="flex-shrink-0">
                <span class="title ps-1">{{ metadata.whitePlayerTitle }}</span>
            </div>
            <div class="text-truncate px-1 flex-shrink-1">
                {{ metadata.whitePlayerName }}
            </div>
            <div v-if="metadata.whitePlayerRating" class="flex-item flex-grow-1 text-start">
                ({{ metadata.whitePlayerRating }})
            </div>
            <div v-if="resultFor('white')" class="flex-shrink-0">
                <span :class="['ms-3 pe-1 fw-bold fs-6', resultClass(resultFor('white'))]">
                    {{ resultFor('white') }}
                </span>
            </div>
        </div>


    </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { Chess } from 'chess.js'
import { TheChessboard } from 'vue3-chessboard'
import { useRouter } from 'vue-router'
import 'vue3-chessboard/style.css'
import { STARTING_FEN } from '@/lib/fen'
import { parseHeaders } from '@/lib/pgn'
import { useGameStore } from '@/stores/game'

const props = withDefaults(defineProps<{ pgn?: string }>(), { pgn: '' })

const game = useGameStore()
const router = useRouter()

const metadata = computed(() => {
    const tags = parseHeaders(props.pgn)
    return {
        whitePlayerTitle: tags.WhiteTitle ?? null,
        whitePlayerName: tags.White ?? null,
        whitePlayerRating: tags.WhiteElo ?? null,
        blackPlayerTitle: tags.BlackTitle ?? null,
        blackPlayerName: tags.Black ?? null,
        blackPlayerRating: tags.BlackElo ?? null,
        gameResult: tags.Result ?? null,
        openingName: tags.Opening ?? null,
    }
})

/** Final position of the game, or the starting position if the PGN cannot be read. */
function finalFen(pgn: string): string {
    try {
        const chess = new Chess()
        chess.loadPgn(pgn)
        return chess.fen()
    } catch {
        return STARTING_FEN
    }
}

const boardConfig = reactive({
    fen: finalFen(props.pgn),
    viewOnly: true, // Make the board read-only
    orientation: 'white' as const,
})

function navigateToAnalysis() {
    try {
        game.loadPgn(props.pgn)
    } catch (error) {
        alert(error instanceof Error ? error.message : 'PGN is invalid or empty.')
        return
    }
    router.push({ name: 'home' })
}

function resultFor(side: 'white' | 'black'): string | null {
    const res = metadata.value.gameResult
    if (!res || res === '*') return null
    if (res === '1-0') return side === 'white' ? '1' : '0'
    if (res === '0-1') return side === 'white' ? '0' : '1'
    if (res === '1/2-1/2') return '½'
    return null
}

function resultClass(result: string | null): string {
    if (result === '1') return 'text-victory '
    if (result === '0') return 'text-danger '
    return 'text-light '
}
</script>

<style scoped>
#eventGameCard {
    width: 270px;
    color: #ddd;
    background-color: #262421;
    border: 1px solid #262421;
    transition: 0.3s;
}

#eventGameCard:hover {
    background-color: #2c2a27;
    border: 1px solid #aaa23a;
}

.title {
    color: #aaa23a;
    font-weight: bold;
}

.overlay {
    position: absolute;
    top: 0;
    left: 0;
    height: inherit;
    width: inherit;
    background-color: rgba(0, 0, 0, 0.4);
    color: white;
    font-weight: bold;
    font-size: 2rem;
    z-index: 100;
    cursor: pointer
}

.text-victory {
    color: #629924;
}

.text-loss {
    color: #cc3333;
}
</style>