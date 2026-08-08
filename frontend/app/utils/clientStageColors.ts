// Single source of truth for stage → color mapping. ClientStage has no
// `color` column (order-based, no migration needed) — the color is derived
// purely from the stage's position, cycling through a fixed palette. Both
// the Kanban column headers and the list view's stage badge call this same
// function so a stage always looks the same regardless of which view it's
// rendered in.
const STAGE_COLOR_PALETTE: readonly string[] = [
    'bg-primary/10 text-primary',
    'bg-success/10 text-success',
    'bg-amber-500/10 text-amber-600',
    'bg-blue-500/10 text-blue-600',
    'bg-purple-500/10 text-purple-600',
    'bg-destructive/10 text-destructive',
    'bg-pink-500/10 text-pink-600',
    'bg-teal-500/10 text-teal-600'
]

export function getClientStageColorClasses(order: number): string {
    const paletteSize = STAGE_COLOR_PALETTE.length
    const index = ((order % paletteSize) + paletteSize) % paletteSize
    return STAGE_COLOR_PALETTE[index]!
}
