import { onMounted, onUnmounted, type Ref } from 'vue'
import { useGameStore } from '@/stores/game'

function isEditable(el: Element | null): boolean {
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || (el as HTMLElement).isContentEditable)
}

/** Arrow keys / Home / End navigate the game, Shift+Enter toggles analysis mode. */
export function useKeyboardNavigation(disabled: Ref<boolean>) {
  const game = useGameStore()

  function onKeyDown(event: KeyboardEvent) {
    if (disabled.value || isEditable(document.activeElement)) return
    switch (event.key) {
      case 'ArrowLeft':
        event.preventDefault()
        game.back()
        break
      case 'ArrowRight':
        event.preventDefault()
        game.forward()
        break
      case 'ArrowUp':
      case 'Home':
        event.preventDefault()
        game.goToStart()
        break
      case 'ArrowDown':
      case 'End':
        event.preventDefault()
        game.goToEnd()
        break
      case 'Enter':
        if (event.shiftKey) {
          event.preventDefault()
          game.toggleAnalysisMode()
        }
        break
    }
  }

  onMounted(() => document.addEventListener('keydown', onKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
}
