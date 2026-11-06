<script setup lang="ts">
import { Skeleton } from '@/components/ui/skeleton'
</script>

<template>
  <div class="event-game-card min-w-0 rounded-(--radius) border border-border bg-card p-2.5" aria-hidden="true">
    <div class="flex items-center gap-2">
      <Skeleton class="h-4 w-8" />
      <Skeleton class="h-4 flex-1" />
      <Skeleton class="h-4 w-6" />
    </div>
    <Skeleton class="my-2 aspect-square w-full" />
    <div class="flex items-center gap-2">
      <Skeleton class="h-4 w-8" />
      <Skeleton class="h-4 flex-1" />
      <Skeleton class="h-4 w-6" />
    </div>
  </div>
</template>
