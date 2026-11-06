<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { ChevronRight, Plus, RefreshCw } from '@lucide/vue'
import EventGame from './EventGame.vue'
import EventGameSkeleton from './EventGameSkeleton.vue'
import IconButton from './IconButton.vue'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Spinner } from '@/components/ui/spinner'

const BATCH = 5

const props = withDefaults(
  defineProps<{
    title: string
    pgnList?: string[]
    shouldRender?: boolean
    initiallyOpen?: boolean
    /** A fetch of the games is in progress. */
    loading?: boolean
    /** Message shown when the event has no games (empty = nothing). */
    emptyText?: string
  }>(),
  { pgnList: () => [], shouldRender: true, initiallyOpen: false, loading: false, emptyText: '' },
)

const emit = defineEmits<{ refresh: [] }>()

const { t } = useTranslation()

const isVisible = ref(props.initiallyOpen)
const visibleCount = ref(BATCH)

// Skeletons only while there is nothing to show yet; afterwards the refresh button spins.
const isLoading = computed(() => props.loading && props.pgnList.length === 0)
const isRefreshing = computed(() => props.loading)
const pgnListToRender = computed(() => props.pgnList.slice(0, visibleCount.value))
const canLoadMore = computed(() => pgnListToRender.value.length < props.pgnList.length && !isLoading.value)

const loadMore = () => {
  visibleCount.value += BATCH
}

const handleRefresh = () => {
  if (!isRefreshing.value) emit('refresh')
}
</script>

<template>
  <Collapsible v-if="shouldRender" v-model:open="isVisible" class="event-section panel">
    <div class="panel-header">
      <CollapsibleTrigger as-child>
        <button
          type="button"
          class="event-toggle -ml-1 flex min-w-0 items-center gap-2 rounded-md p-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight
            class="size-5 shrink-0 text-olive transition-transform"
            :class="{ 'rotate-90': isVisible }"
            aria-hidden="true"
          />
          <h3 class="truncate text-lg font-semibold text-foreground">{{ title }}</h3>
        </button>
      </CollapsibleTrigger>
      <IconButton :label="t('live.refreshData')" variant="outline" size="icon-sm" :disabled="isRefreshing" @click="handleRefresh">
        <Spinner v-if="isRefreshing" aria-hidden="true" />
        <RefreshCw v-else aria-hidden="true" />
      </IconButton>
    </div>

    <CollapsibleContent>
      <div class="event-body grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-(--gap) p-(--pad)">
        <template v-if="isLoading">
          <EventGameSkeleton v-for="i in 3" :key="`skeleton-${i}`" />
        </template>

        <p v-else-if="pgnList.length === 0 && emptyText" class="col-span-full py-8 text-center text-muted-foreground" role="status">
          {{ emptyText }}
        </p>

        <template v-else>
          <EventGame v-for="(pgn, index) in pgnListToRender" :key="`pgn-${index}`" :pgn="pgn" class="flex-item" />
        </template>
      </div>

      <div v-if="canLoadMore" class="flex justify-center pb-(--pad)">
        <Button id="load-more" variant="outline" @click="loadMore">
          <Plus aria-hidden="true" />{{ t('live.showMore') }}
        </Button>
      </div>
    </CollapsibleContent>
  </Collapsible>
</template>
