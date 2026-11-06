<script setup lang="ts">
/** Icon-only button with a tooltip and an accessible name (the label is both). */
import type { ButtonVariants } from '@/components/ui/button'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

withDefaults(
  defineProps<{
    label: string
    variant?: ButtonVariants['variant']
    size?: ButtonVariants['size']
    /** Toggle state (adds aria-pressed). */
    pressed?: boolean
    disabled?: boolean
    /** Keyboard shortcut shown in the tooltip. */
    shortcut?: string
  }>(),
  { variant: 'ghost', size: 'icon', pressed: undefined, disabled: false, shortcut: undefined },
)
</script>

<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <Button :variant="variant" :size="size" :disabled="disabled" :aria-label="label" :aria-pressed="pressed">
        <slot />
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      {{ label }}
      <Kbd v-if="shortcut" class="ml-2">{{ shortcut }}</Kbd>
    </TooltipContent>
  </Tooltip>
</template>
