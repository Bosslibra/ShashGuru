<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useTranslation } from 'i18next-vue'
import { RotateCcw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { MIN_DEPTH, MAX_DEPTH, MIN_SHOW_LINES, MAX_SHOW_LINES } from '@/constants/evaluation'
import { useSettingsStore } from '@/stores/settings'

const { t } = useTranslation()
const settings = useSettingsStore()

// Toggles and line count apply immediately.
const localEnabled = computed({
  get: () => settings.enabled,
  set: (value: boolean) => (settings.enabled = value),
})
const localShowBestMove = computed({
  get: () => settings.showBestMove,
  set: (value: boolean) => (settings.showBestMove = value),
})
const localShowLines = computed({
  get: () => settings.lines,
  set: (value: number) => (settings.lines = value),
})

// Changing the depth triggers a (slow) new evaluation, so it is applied when the dialog closes.
const localDepth = ref<number>(settings.depth)

onUnmounted(() => {
  if (localDepth.value !== settings.depth) settings.depth = localDepth.value
})

function resetToDefaults() {
  settings.reset()
  localDepth.value = settings.depth
}
</script>

<template>
  <div class="evaluation-settings space-y-6">
    <!-- Engine on/off -->
    <div class="flex items-center justify-between gap-4">
      <Label for="engine-toggle" class="panel-label text-foreground!">{{ t('settings.engineAnalysis') }}</Label>
      <div class="flex items-center gap-3">
        <span class="num w-7 text-right text-xs font-semibold text-muted-foreground">
          {{ localEnabled ? t('common.on') : t('common.off') }}
        </span>
        <Switch id="engine-toggle" v-model="localEnabled" />
      </div>
    </div>

    <template v-if="localEnabled">
      <div class="space-y-3">
        <Label for="depth-slider" class="num text-sm">{{ t('settings.depth', { value: localDepth }) }}</Label>
        <Slider
          id="depth-slider"
          :model-value="[localDepth]"
          :min="MIN_DEPTH"
          :max="MAX_DEPTH"
          :step="1"
          :thumb-label="t('settings.depth', { value: localDepth })"
          @update:model-value="(v) => (localDepth = v?.[0] ?? localDepth)"
        />
      </div>

      <div class="flex items-center justify-between gap-4">
        <Label for="best-move-toggle" class="text-sm">{{ t('settings.showBestMove') }}</Label>
        <Switch id="best-move-toggle" v-model="localShowBestMove" />
      </div>

      <div class="space-y-3">
        <Label for="lines-slider" class="num text-sm">{{ t('settings.showLines', { value: localShowLines }) }}</Label>
        <Slider
          id="lines-slider"
          :model-value="[localShowLines]"
          :min="MIN_SHOW_LINES"
          :max="MAX_SHOW_LINES"
          :step="1"
          :thumb-label="t('settings.showLines', { value: localShowLines })"
          @update:model-value="(v) => (localShowLines = v?.[0] ?? localShowLines)"
        />
      </div>

      <Button variant="outline" size="sm" class="w-full" @click="resetToDefaults">
        <RotateCcw aria-hidden="true" />{{ t('settings.reset') }}
      </Button>
    </template>
  </div>
</template>
