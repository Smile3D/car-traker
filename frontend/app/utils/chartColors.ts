export const CHART_PRIMARY_COLOR = '#1E40AF'
export const CHART_ACCENT_COLOR = '#D97706'
export const CHART_PRIMARY_FILL = 'rgba(30, 64, 175, 0.12)'
export const CHART_GRID_COLOR = '#E2E8F0'

export const CHART_SUCCESS_COLOR = '#16A34A'
export const CHART_DESTRUCTIVE_COLOR = '#DC2626'
export const CHART_BLUE_COLOR = '#2563EB'
export const CHART_MUTED_COLOR = '#94A3B8'
export const CHART_VIOLET_COLOR = '#7C3AED'

export const CHART_LISTING_STATUS_COLORS: Record<'draft' | 'active' | 'reserved' | 'sold' | 'removed' | 'on_service', string> = {
  draft: CHART_MUTED_COLOR,
  active: CHART_SUCCESS_COLOR,
  reserved: CHART_ACCENT_COLOR,
  sold: CHART_BLUE_COLOR,
  removed: CHART_DESTRUCTIVE_COLOR,
  on_service: CHART_VIOLET_COLOR,
}
