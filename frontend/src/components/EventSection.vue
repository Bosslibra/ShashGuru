<template>
    <div v-if="shouldRender" class="card-like event-section mx-5 mb-2 pb-3 position-relative">
        <div class="d-flex flex-row align-items-center justify-content-between p-3 event-header">
            <div class="fs-4 flex-shrink-0 cursor-pointer" @click="toggleVisibility">
                <span>{{ title }}</span>
                <span class="material-icons ms-1">
                    {{ isVisible ? 'keyboard_arrow_down' : 'chevron_right' }}
                </span>
            </div>
            <div class="d-flex gap-2">
                <!-- Refresh Button -->
                <button 
                    class="btn btn-outline-secondary btn-sm refresh-btn" 
                    @click="handleRefresh"
                    :disabled="isRefreshing"
                    title="Refresh PGN data"
                >
                    <span v-if="!isRefreshing" class="material-icons">refresh</span>
                    <span v-else class="spinner-border spinner-border-sm"></span>
                </button>
            </div>
        </div>

        <!-- Body -->
        <transition name="slide">
            <div v-if="isVisible" class="d-flex flex-row flex-wrap event-body">

                <template v-if="isLoading">
                    <EventGameSkeleton v-for="i in 3"
                        :key="`skeleton-${i}`" />
                </template>

                <template v-else>
                    <EventGame v-for="(pgn, index) in pgnListToRender" :key="`pgn-${index}`" :pgn="pgn"
                        class="flex-item shadow" />
                </template>

            </div>
        </transition>
        <span v-if="isVisible && (pgnListToRender.length < pgnList.length) && !isLoading" class="material-icons-outlined"
            id="load-more" @click="loadMore" title="Show more">
            add
        </span>
        
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import EventGame from './EventGame.vue'
import EventGameSkeleton from './EventGameSkeleton.vue'

const BATCH = 5

const props = withDefaults(
    defineProps<{
        title: string
        pgnList?: string[]
        shouldRender?: boolean
        initiallyOpen?: boolean
        /** A fetch of the games is in progress. */
        loading?: boolean
    }>(),
    { pgnList: () => [], shouldRender: true, initiallyOpen: false, loading: false },
)

const emit = defineEmits<{ refresh: [] }>()

const isVisible = ref(props.initiallyOpen)
const visibleCount = ref(BATCH)

// Skeletons only while there is nothing to show yet; afterwards the refresh button spins.
const isLoading = computed(() => props.loading && props.pgnList.length === 0)
const isRefreshing = computed(() => props.loading)
const pgnListToRender = computed(() => props.pgnList.slice(0, visibleCount.value))

const loadMore = () => {
    visibleCount.value += BATCH
}

const toggleVisibility = () => {
    isVisible.value = !isVisible.value
}

const handleRefresh = () => {
    if (!isRefreshing.value) emit('refresh')
}
</script>


<style scoped>
#load-more {
    position: absolute;
    background: #aaa23a;
    color: black;
    border-radius: 50%;
    padding: 10px;
    z-index: 300;
    bottom: -20px;
    left: 50%;
    cursor: pointer;
}

.refresh-btn {
    border-color: #aaa23a;
    color: #aaa23a;
    background-color: transparent;
}

.refresh-btn:hover {
    background-color: #aaa23a;
    color: white;
    border-color: #aaa23a;
}

.refresh-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.refresh-btn .material-icons {
    font-size: 18px;
}

.card-like {
    background-color: #1c1c1c;
    border: 1px solid #333;
    border-radius: 10px;
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    background-color: #232323;
    border-bottom: 1px solid #333;
    transition: background 0.2s;
}

.event-header:hover {
    background-color: #2f2f2f;
}

.event-body {
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}


.fade-highlight-enter-active {
    transition: background-color 1.5s ease;
}

.fade-highlight-enter-from {
    background-color: #444a2f;
    /* highlight color */
}

.fade-highlight-enter-to {
    background-color: transparent;
}

.highlight-container {
    border: 2px solid #aaa23a;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 1rem;
}


.cursor-pointer {
    cursor: pointer;
}

.transition-transform {
    transition: transform 0.3s ease;
}

.rotate-90 {
    transform: rotate(90deg);
}

.toggle-arrow {
    font-size: 1.5rem;
    /* make icon size match your text */
    line-height: 1;
    /* removes extra vertical padding */
    vertical-align: middle;
}

.slide-enter-active,
.slide-leave-active {
    transition: max-height 0.3s ease, opacity 0.3s ease;
    overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
    max-height: 0;
    opacity: 0;
}

.slide-enter-to,
.slide-leave-from {
    max-height: 1000px;
    /* something large enough for your content */
    opacity: 1;
}
</style>