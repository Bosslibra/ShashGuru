/** Icons, colours and groups of the move annotations (move quality and Shashin position types). */
import type { Component } from 'vue'
import {
  BookOpen,
  Check,
  ChevronDown,
  ChevronsDown,
  ChevronsUp,
  ChevronUp,
  CircleHelp,
  CircleX,
  HeartCrack,
  Minus,
  Scale,
  Shield,
  Sparkles,
  Star,
  Swords,
  ThumbsUp,
  Tornado,
  TriangleAlert,
  Zap,
} from '@lucide/vue'

export interface AnnotationIconMeta {
  icon: Component
  /** Tailwind text colour class: this is the colour coding of the annotation. */
  color: string
}

/** Move quality, from the best to the worst. */
export const MOVE_EVALUATION_META: Record<string, AnnotationIconMeta> = {
  brilliant: { icon: Sparkles, color: 'text-eval-1' },
  great: { icon: Zap, color: 'text-eval-2' },
  best: { icon: Star, color: 'text-eval-2' },
  excellent: { icon: ThumbsUp, color: 'text-eval-3' },
  good: { icon: Check, color: 'text-eval-4' },
  book: { icon: BookOpen, color: 'text-muted-foreground' },
  inaccuracy: { icon: TriangleAlert, color: 'text-warning' },
  mistake: { icon: CircleHelp, color: 'text-eval-6' },
  blunder: { icon: CircleX, color: 'text-destructive' },
  'missed-win': { icon: HeartCrack, color: 'text-eval-7' },
}

/** Move quality types in the order shown in the menu. */
export const MOVE_EVALUATION_TYPES = [
  'brilliant',
  'great',
  'best',
  'excellent',
  'good',
  'book',
  'inaccuracy',
  'mistake',
  'blunder',
  'missed-win',
] as const

/** Shashin family -> icon and colour: Tal (attack, warm), Petrosian (defence, cool), ... */
const FAMILY_META = {
  tal: { icon: Swords, color: 'text-eval-6' },
  capablanca: { icon: Scale, color: 'text-cream' },
  petrosian: { icon: Shield, color: 'text-eval-1' },
  chaos: { icon: Tornado, color: 'text-eval-7' },
} as const

/** How far the position leans towards its family: shown as a small chevron next to the icon. */
export const SHASHIN_LEVEL_ICONS: Record<string, Component> = {
  high: ChevronsUp,
  'high-middle': ChevronUp,
  middle: Minus,
  'middle-low': ChevronDown,
  low: ChevronsDown,
}

export interface ShashinMeta extends AnnotationIconMeta {
  level: string | null
}

/** Shashin types, grouped by playing style; `key` selects the group title translation. */
export const SHASHIN_GROUPS = [
  { key: 'tal', types: ['high-tal', 'high-middle-tal', 'middle-tal', 'middle-low-tal', 'low-tal'] },
  { key: 'capablanca', types: ['capablanca'] },
  {
    key: 'petrosian',
    types: ['high-petrosian', 'high-middle-petrosian', 'middle-petrosian', 'middle-low-petrosian', 'low-petrosian'],
  },
  { key: 'chaos', types: ['chaos-all'] },
] as const

/** Icon, colour and level for a Shashin type such as 'high-middle-tal' or 'chaos-all'. */
export function shashinMeta(type?: string | null): ShashinMeta | null {
  if (!type) return null
  if (type === 'chaos-all') return { ...FAMILY_META.chaos, level: null }
  if (type === 'capablanca') return { ...FAMILY_META.capablanca, level: null }
  for (const family of ['tal', 'petrosian'] as const) {
    if (type.endsWith(`-${family}`)) {
      const level = type.slice(0, -(family.length + 1))
      return { ...FAMILY_META[family], level }
    }
  }
  return null
}

export function moveEvaluationMeta(type?: string | null): AnnotationIconMeta | null {
  return (type && MOVE_EVALUATION_META[type]) || null
}
