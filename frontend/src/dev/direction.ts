/**
 * DEV ONLY. Lets us flip between the visual directions while choosing one.
 * Only imported behind `import.meta.env.DEV`, so it never reaches the production bundle.
 */
export const DIRECTIONS = [
  { id: 'scoresheet', label: 'Scoresheet' },
  { id: 'tavolo', label: 'Tavolo' },
  { id: 'editoriale', label: 'Editoriale' },
] as const

export type DirectionId = (typeof DIRECTIONS)[number]['id']

const STORAGE_KEY = 'shashguru.dev.direction'
const DEFAULT: DirectionId = 'scoresheet'

function isDirection(value: string | null | undefined): value is DirectionId {
  return DIRECTIONS.some((d) => d.id === value)
}

function readStored(): DirectionId | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isDirection(value) ? value : null
  } catch {
    return null
  }
}

export function getDirection(): DirectionId {
  const current = document.documentElement.dataset.dir
  return isDirection(current) ? current : DEFAULT
}

export function setDirection(id: DirectionId) {
  document.documentElement.dataset.dir = id
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* storage unavailable: the choice just is not remembered */
  }
}

/** `?dir=tavolo` wins over the remembered choice. */
export function initDirection() {
  const fromQuery = new URLSearchParams(window.location.search).get('dir')
  setDirection(isDirection(fromQuery) ? fromQuery : (readStored() ?? DEFAULT))
}
